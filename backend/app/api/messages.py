"""Messaging, attachments and CSAT (US15) + internal notes (US9)."""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import schemas
from ..config import get_settings
from ..db import get_db, utcnow
from ..models import CSAT, Attachment, Escalation, Message, Notification, Request, Role, Status, Unit, User
from ..security import current_user, require_roles, sign_file, verify_file_signature
from ..services import notifications, suggestions, workflow
from .common import get_request_or_404

router = APIRouter(tags=["messaging"])

ALLOWED_TYPES = {
    "pdf": ("application/pdf", [b"%PDF"]),
    "jpg": ("image/jpeg", [b"\xff\xd8\xff"]),
    "jpeg": ("image/jpeg", [b"\xff\xd8\xff"]),
    "png": ("image/png", [b"\x89PNG\r\n\x1a\n"]),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", [b"PK\x03\x04"]),
}
EICAR = b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"


def scan_for_malware(data: bytes) -> bool:
    """Minimal built-in scanner (EICAR test signature + PE executables). Swap for ClamAV in production."""
    return EICAR in data or data[:2] == b"MZ"


def attachment_out(a: Attachment, viewer: User) -> schemas.AttachmentOut:
    exp, sig = sign_file(a.id, viewer.id)
    return schemas.AttachmentOut(id=a.id, filename=a.filename, content_type=a.content_type, size=a.size,
                                 url=f"/api/v1/files/{a.id}?uid={viewer.id}&exp={exp}&sig={sig}")


def message_out(m: Message, viewer: User) -> schemas.MessageOut:
    return schemas.MessageOut(id=m.id, request_id=m.request_id, author=schemas.UserBrief.model_validate(m.author),
                              author_role=m.author.role, body=m.body, is_internal=m.is_internal, read_at=m.read_at,
                              created_at=m.created_at, attachments=[attachment_out(a, viewer) for a in m.attachments])


def post_message(db: Session, req: Request, author: User, body: str, is_internal: bool = False,
                 attachments: list[Attachment] | None = None) -> Message:
    staff = author.role in Role.STAFF
    msg = Message(request_id=req.id, author_id=author.id, body=body, is_internal=is_internal and staff)
    msg.author = author
    db.add(msg)
    db.flush()
    for a in attachments or []:
        a.message_id = msg.id
        a.is_internal = msg.is_internal
    db.flush()
    db.refresh(msg)

    suggestions.invalidate(req.id)  # smart replies depend on the latest messages
    if staff and not msg.is_internal and req.first_response_at is None:
        req.first_response_at = utcnow()
    req.updated_at = utcnow()

    # Internal notes go only to staff listening on the request; never to the student's channels.
    payload = {"event": "message", "request_id": req.id, "message_id": msg.id, "internal": msg.is_internal,
               "author_id": author.id}
    notifications.queue_push(db, f"request:{req.id}" + (":staff" if msg.is_internal else ""), payload)
    if msg.is_internal:
        return msg
    if staff:
        notifications.notify(db, req.student, "reply", f"New reply on {req.id}", body[:200] or "New attachment", req)
    elif req.assignee:
        notifications.notify(db, req.assignee, "reply", f"Student replied on {req.id}", body[:200], req, email=False)
        if req.status == Status.WAITING:
            # Student answered: SLA resumes and the request goes back to the agent.
            workflow.transition(db, req, Status.IN_PROGRESS, actor=author, reason="system",
                                note="Student replied", notify_student=False)
    elif req.status == Status.WAITING:
        workflow.transition(db, req, Status.IN_PROGRESS, actor=author, reason="system", note="Student replied",
                            notify_student=False)
    return msg


@router.get("/requests/{request_id}/messages", response_model=list[schemas.MessageOut])
def list_messages(request_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    req = get_request_or_404(db, request_id, user)
    q = db.query(Message).filter_by(request_id=req.id)
    if user.role not in Role.STAFF:
        q = q.filter(Message.is_internal.is_(False))
    msgs = q.order_by(Message.id).all()
    mark_read(db, req, user, msgs)
    db.commit()
    return [message_out(m, user) for m in msgs]


def mark_read(db: Session, req: Request, reader: User, msgs: list[Message]) -> None:
    reader_staff = reader.role in Role.STAFF
    now = utcnow()
    ids = []
    for m in msgs:
        if m.read_at is None and not m.is_internal and (m.author.role in Role.STAFF) != reader_staff:
            m.read_at = now
            ids.append(m.id)
    if ids:
        notifications.queue_push(db, f"request:{req.id}", {"event": "read", "request_id": req.id, "message_ids": ids,
                                                           "reader_id": reader.id, "at": now.isoformat() + "Z"})


@router.post("/requests/{request_id}/messages", response_model=schemas.MessageOut, status_code=201)
def create_message(request_id: str, body: schemas.MessageIn, db: Session = Depends(get_db),
                   user: User = Depends(current_user)):
    req = get_request_or_404(db, request_id, user)
    if body.is_internal and user.role not in Role.STAFF:
        raise HTTPException(403, "Students cannot write internal notes")
    if req.status == Status.CLOSED:
        raise HTTPException(409, {"message": "Request is closed"})
    atts = []
    if body.attachment_ids:
        atts = db.query(Attachment).filter(Attachment.id.in_(body.attachment_ids), Attachment.request_id == req.id,
                                           Attachment.uploader_id == user.id, Attachment.message_id.is_(None)).all()
        if len(atts) != len(set(body.attachment_ids)):
            raise HTTPException(422, "Invalid attachment ids")
    if not body.body and not atts:
        raise HTTPException(422, "Message is empty")
    msg = post_message(db, req, user, body.body, body.is_internal, atts)
    db.commit()
    return message_out(msg, user)


@router.post("/requests/{request_id}/attachments", response_model=schemas.AttachmentOut, status_code=201)
async def upload_attachment(request_id: str, file: UploadFile = File(...), db: Session = Depends(get_db),
                            user: User = Depends(current_user)):
    req = get_request_or_404(db, request_id, user)
    s = get_settings()
    name = (file.filename or "file").replace("\\", "/").rsplit("/", 1)[-1][:180]
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED_TYPES:
        raise HTTPException(415, "Only PDF, JPG, PNG and DOCX files are allowed")
    limit = s.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"File exceeds {s.max_upload_mb} MB")
    content_type, magics = ALLOWED_TYPES[ext]
    if not any(data.startswith(mg) for mg in magics):
        raise HTTPException(415, "File content does not match its extension")
    if scan_for_malware(data):
        raise HTTPException(422, "File rejected by virus scan")
    key = f"{req.id}/{uuid.uuid4().hex}.{ext}"
    path = s.upload_dir / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    att = Attachment(request_id=req.id, uploader_id=user.id, filename=name, content_type=content_type,
                     size=len(data), storage_key=key)
    db.add(att)
    db.commit()
    return attachment_out(att, user)


@router.get("/files/{attachment_id}", include_in_schema=True, summary="Download via signed URL")
def download(attachment_id: int, uid: int, exp: int, sig: str, db: Session = Depends(get_db)):
    if not verify_file_signature(attachment_id, uid, exp, sig):
        raise HTTPException(403, "Link expired or invalid")
    att = db.get(Attachment, attachment_id)
    viewer = db.get(User, uid)
    if att is None or viewer is None:
        raise HTTPException(404, "Not found")
    if att.is_internal and viewer.role not in Role.STAFF:
        raise HTTPException(404, "Not found")
    path = get_settings().upload_dir / att.storage_key
    if not path.exists():
        raise HTTPException(404, "File missing")
    return FileResponse(path, media_type=att.content_type, filename=att.filename)


@router.post("/requests/{request_id}/csat", response_model=schemas.CSATOut, status_code=201)
def rate(request_id: str, body: schemas.CSATIn, db: Session = Depends(get_db),
         user: User = Depends(require_roles(Role.STUDENT))):
    req = get_request_or_404(db, request_id, user)
    if req.status not in (Status.RESOLVED, Status.CLOSED):
        raise HTTPException(409, {"message": "You can rate only resolved requests"})
    if req.csat:
        raise HTTPException(409, {"message": "Already rated"})
    c = CSAT(request_id=req.id, rating=body.rating, comment=body.comment)
    db.add(c)
    db.flush()
    if body.rating <= 2:
        unit = db.get(Unit, req.unit_id) if req.unit_id else None
        head = db.get(User, unit.head_user_id) if unit and unit.head_user_id else None
        req.escalated = True
        if req.status == Status.RESOLVED:
            workflow.transition(db, req, Status.REOPENED, actor=user, reason="system",
                                note=f"Low CSAT ({body.rating}/5): reopened for unit head review", notify_student=False)
        if head:
            notifications.notify(db, head, "low_csat", f"Low rating on {req.id}: {body.rating}/5",
                                 body.comment or "No comment", req)
        db.add(Escalation(request_id=req.id, kind="low_csat", target="-",
                          notified_user_id=head.id if head else None,
                          detail=f"Rating {body.rating}/5: {body.comment}"))
    notifications.queue_push(db, f"request:{req.id}", {"event": "csat", "request_id": req.id, "rating": body.rating})
    db.commit()
    return c


@router.get("/notifications", response_model=list[schemas.NotificationOut], tags=["notifications"])
def my_notifications(db: Session = Depends(get_db), user: User = Depends(current_user),
                     unread_only: bool = False, limit: int = Query(30, le=100)):
    q = db.query(Notification).filter_by(user_id=user.id)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    return q.order_by(Notification.id.desc()).limit(limit).all()


@router.get("/notifications/unread-count", tags=["notifications"])
def unread_count(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return {"count": db.query(Notification).filter_by(user_id=user.id, is_read=False).count()}


@router.post("/notifications/read", tags=["notifications"])
def mark_notifications_read(ids: list[int] | None = None, db: Session = Depends(get_db),
                            user: User = Depends(current_user)):
    q = db.query(Notification).filter(Notification.user_id == user.id, Notification.is_read.is_(False))
    if ids:
        q = q.filter(Notification.id.in_(ids))
    q.update({Notification.is_read: True}, synchronize_session=False)
    db.commit()
    count = db.query(Notification).filter_by(user_id=user.id, is_read=False).count()
    notifications.hub.publish(f"user:{user.id}", {"event": "unread_count", "count": count})
    return {"count": count}
