"""In-process WebSocket hub with channels "user:{id}" and "request:{id}".

Sync code (endpoints run in a threadpool, the scheduler in its own thread) calls publish();
messages are handed to the event loop thread-safely. For multi-instance deployments this
class is the single place to swap in Redis pub/sub.
"""
import asyncio
import json
import logging
from collections import defaultdict

from fastapi import WebSocket

log = logging.getLogger(__name__)


class Hub:
    def __init__(self) -> None:
        self.channels: dict[str, set[WebSocket]] = defaultdict(set)
        self.online_users: dict[int, int] = defaultdict(int)  # user_id -> open sockets
        self.loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    async def connect(self, ws: WebSocket, user_id: int, channels: list[str]) -> None:
        await ws.accept()
        for ch in channels:
            self.channels[ch].add(ws)
        self.online_users[user_id] += 1

    def disconnect(self, ws: WebSocket, user_id: int, channels: list[str]) -> None:
        for ch in channels:
            self.channels[ch].discard(ws)
        self.online_users[user_id] = max(0, self.online_users[user_id] - 1)

    def is_online(self, user_id: int) -> bool:
        return self.online_users.get(user_id, 0) > 0

    async def _send(self, channel: str, payload: dict, exclude: WebSocket | None = None) -> None:
        data = json.dumps(payload, default=str)
        for ws in list(self.channels.get(channel, ())):
            if ws is exclude:
                continue
            try:
                await ws.send_text(data)
            except Exception:  # client went away
                self.channels[channel].discard(ws)

    async def broadcast(self, channel: str, payload: dict, exclude: WebSocket | None = None) -> None:
        await self._send(channel, payload, exclude)

    def publish(self, channel: str, payload: dict) -> None:
        if self.loop is None or not self.loop.is_running():
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is self.loop:
            self.loop.create_task(self._send(channel, payload))
        else:
            asyncio.run_coroutine_threadsafe(self._send(channel, payload), self.loop)


hub = Hub()
