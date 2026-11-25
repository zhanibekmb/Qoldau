"""Database-backed fixed-window limits shared across API workers."""

import hashlib
import ipaddress
import re
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .config import Settings
from .db import SessionLocal
from .models import RateLimitBucket
from .security import decode_token


@dataclass(frozen=True)
class Policy:
    scope: str
    limit: int
    seconds: int
    by_ip: bool = False


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after


def client_ip(request: Request, trusted_proxy_cidrs: list[str]) -> str:
    peer = request.client.host if request.client else "unknown"
    try:
        networks = [ipaddress.ip_network(cidr, strict=False) for cidr in trusted_proxy_cidrs]
        address = ipaddress.ip_address(peer)
    except ValueError:
        return peer
    if not any(address in network for network in networks):
        return peer
    forwarded = request.headers.get("x-forwarded-for", "")
    if not forwarded:
        return peer
    try:
        chain = [ipaddress.ip_address(part.strip()) for part in forwarded.split(",")]
    except ValueError:
        return peer
    for address in reversed(chain):
        if not any(address in network for network in networks):
            return str(address)
    return str(chain[0])


def identity(request: Request, settings: Settings, by_ip: bool = False) -> str:
    ip = client_ip(request, settings.trusted_proxy_cidrs)
    if not by_ip:
        scheme, _, token = request.headers.get("authorization", "").partition(" ")
        if scheme.lower() == "bearer" and token:
            try:
                return f"user:{decode_token(token, 'access')}"
            except (HTTPException, ValueError, TypeError):
                pass
    return f"ip:{ip}"


def policy_for(request: Request, settings: Settings) -> Policy | None:
    method, path = request.method, request.url.path.rstrip("/")
    if method == "POST" and path == "/api/v1/auth/login":
        return Policy("login-ip", settings.rate_limit_login_ip_per_minute, 60, by_ip=True)
    if method == "POST" and path == "/api/v1/auth/refresh":
        return Policy("refresh", settings.rate_limit_refresh_per_minute, 60, by_ip=True)
    if method == "POST" and path == "/api/v1/auth/change-password":
        return Policy("password-change", settings.rate_limit_login_account_per_minute, 60)
    if method == "POST" and path == "/api/v1/requests":
        return Policy("request-create", settings.rate_limit_write_per_hour, 3600)
    if method == "POST" and re.fullmatch(r"/api/v1/requests/[^/]+/messages", path):
        return Policy("message", settings.rate_limit_message_per_minute, 60)
    if method == "POST" and re.fullmatch(r"/api/v1/requests/[^/]+/attachments", path):
        return Policy("attachment", settings.rate_limit_write_per_hour, 3600)
    if method == "POST" and path in ("/api/v1/ai/classify", "/api/v1/ai/similar"):
        return Policy("ai-query", settings.rate_limit_ai_per_minute, 60)
    if method == "GET" and re.fullmatch(r"/api/v1/ai/suggestions/[^/]+", path):
        return Policy("ai-query", settings.rate_limit_ai_per_minute, 60)
    if method == "POST" and path in ("/api/v1/export/excel", "/api/v1/export/pdf"):
        return Policy("export", settings.rate_limit_export_per_hour, 3600)
    if method == "POST" and path == "/api/v1/ai/retrain":
        return Policy("retrain", settings.rate_limit_retrain_per_hour, 3600)
    return None


def enforce_limit(scope: str, subject: str, limit: int, seconds: int) -> tuple[int, int]:
    """Atomically increment a hashed bucket, then return count and seconds to reset."""
    if limit < 1 or seconds < 1:
        raise ValueError("Rate limits and windows must be positive")
    now = int(time.time())
    window_start = now - now % seconds
    expires_at = window_start + seconds
    retry_after = max(1, expires_at - now)
    key = hashlib.sha256(f"{scope}\0{subject}\0{window_start}".encode()).hexdigest()
    with SessionLocal() as db:
        dialect = db.bind.dialect.name
        if dialect == "postgresql":
            stmt = pg_insert(RateLimitBucket)
        elif dialect == "sqlite":
            stmt = sqlite_insert(RateLimitBucket)
        else:
            raise RuntimeError(f"Unsupported rate-limit database: {dialect}")
        stmt = stmt.values(key=key, count=1, expires_at=expires_at)
        stmt = stmt.on_conflict_do_update(index_elements=[RateLimitBucket.key],
                                          set_={"count": RateLimitBucket.count + 1})
        count = db.execute(stmt.returning(RateLimitBucket.count)).scalar_one()
        if int(key[:4], 16) % 100 == 0:
            db.execute(delete(RateLimitBucket).where(RateLimitBucket.expires_at < now))
        db.commit()
    if count > limit:
        raise RateLimitExceeded(retry_after)
    return count, retry_after
