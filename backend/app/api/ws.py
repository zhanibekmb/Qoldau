"""WebSocket endpoints: /ws/notifications (user + unit feed) and /ws/requests/{id} (chat, typing, receipts)."""
import asyncio
import json

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from ..db import SessionLocal, utcnow
from ..models import Message, Request, Role, User
from ..security import user_from_token
from ..services.realtime import hub
from .common import can_view

router = APIRouter()


def _auth(token: str | None, mark_seen: bool = False, request_id: str | None = None):
    if not token:
        return None
    db = SessionLocal()
    try:
        user = user_from_token(db, token)
        if user.must_change_password:
            return None
        if request_id:
            req = db.get(Request, request_id)
            if req is None or not can_view(db, user, req):
                return None
        if mark_seen:
            user.last_seen_at = utcnow()
            db.commit()
        db.expunge(user)
        return user
    except HTTPException:
        return None
    finally:
        db.close()


async def _receive_authorized(ws: WebSocket) -> str:
    while True:
        try:
            message = await asyncio.wait_for(ws.receive_text(), timeout=5)
        except TimeoutError:
            if not await hub.ensure_authorized(ws):
                raise WebSocketDisconnect(code=4401)
            continue
        if not await hub.ensure_authorized(ws):
            raise WebSocketDisconnect(code=4401)
        return message


@router.websocket("/ws/notifications")
async def ws_notifications(ws: WebSocket, token: str | None = None):
    user = await asyncio.to_thread(_auth, token, True)
    if user is None:
        await ws.close(code=4401)
        return
    channels = [f"user:{user.id}"]
    if user.role in Role.STAFF:
        channels.append("staff")
        if user.unit_id:
            channels.append(f"unit:{user.unit_id}")
    await hub.connect(ws, user.id, channels, lambda: _auth(token) is not None)
    try:
        while True:
            msg = await _receive_authorized(ws)
            if msg == "ping":
                await ws.send_text(json.dumps({"event": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(ws, user.id, channels)


@router.websocket("/ws/requests/{request_id}")
async def ws_request(ws: WebSocket, request_id: str, token: str | None = None):
    user = await asyncio.to_thread(_auth, token, True)
    if user is None:
        await ws.close(code=4401)
        return
    db = SessionLocal()
    try:
        req = db.get(Request, request_id.upper())
        allowed = req is not None and can_view(db, user, req)
    finally:
        db.close()
    if not allowed:
        await ws.close(code=4403)
        return
    staff = user.role in Role.STAFF
    channels = [f"request:{req.id}"] + ([f"request:{req.id}:staff"] if staff else [])
    await hub.connect(ws, user.id, channels, lambda: _auth(token, request_id=req.id) is not None)
    try:
        while True:
            try:
                data = json.loads(await _receive_authorized(ws))
            except ValueError:
                continue
            if not isinstance(data, dict):
                continue
            kind = data.get("type")
            if kind == "typing":
                await hub.broadcast(f"request:{req.id}", {"event": "typing", "request_id": req.id,
                                                          "user_id": user.id, "name": user.name,
                                                          "is_typing": bool(data.get("is_typing", True))}, exclude=ws)
            elif kind == "read":
                await asyncio.to_thread(_mark_read, req.id, user.id, staff)
            elif kind == "ping":
                await ws.send_text(json.dumps({"event": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(ws, user.id, channels)


def _mark_read(request_id: str, reader_id: int, reader_staff: bool) -> None:
    db = SessionLocal()
    try:
        msgs = (db.query(Message).join(User, User.id == Message.author_id)
                .filter(Message.request_id == request_id, Message.read_at.is_(None), Message.is_internal.is_(False))
                .all())
        now = utcnow()
        ids = [m.id for m in msgs if (m.author.role in Role.STAFF) != reader_staff]
        for m in msgs:
            if m.id in ids:
                m.read_at = now
        db.commit()
        if ids:
            hub.publish(f"request:{request_id}", {"event": "read", "request_id": request_id, "message_ids": ids,
                                                  "reader_id": reader_id, "at": now.isoformat() + "Z"})
    finally:
        db.close()
