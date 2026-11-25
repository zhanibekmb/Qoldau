import hashlib
import hmac
import time
from datetime import timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db, utcnow
from .models import Role, User

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def hash_new_password(password: str) -> str:
    if len(password.encode()) > 72:
        raise HTTPException(422, "Password must be at most 72 bytes UTF-8")
    return hash_password(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def _token(user: User, kind: str, ttl: timedelta) -> str:
    now = int(time.time())
    payload = {"sub": str(user.id), "role": user.role, "type": kind, "ver": user.session_version,
               "iat": now, "exp": now + int(ttl.total_seconds())}
    return jwt.encode(payload, get_settings().secret_key, algorithm="HS256")


def create_tokens(user: User) -> dict:
    s = get_settings()
    return {
        "access_token": _token(user, "access", timedelta(minutes=s.access_token_minutes)),
        "refresh_token": _token(user, "refresh", timedelta(days=s.refresh_token_days)),
        "token_type": "bearer",
    }


def _token_claims(token: str, kind: str) -> tuple[int, int]:
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
        if payload.get("type") != kind:
            raise ValueError("Wrong token type")
        return int(payload["sub"]), int(payload.get("ver", 0))
    except (jwt.PyJWTError, KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc


def decode_token(token: str, kind: str) -> int:
    return _token_claims(token, kind)[0]


def user_from_token(db: Session, token: str, kind: str = "access") -> User:
    user_id, version = _token_claims(token, kind)
    user = db.get(User, user_id)
    if not user or not user.is_active or user.session_version != version:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session invalid or expired")
    return user


def authenticated_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                       db: Session = Depends(get_db)) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return user_from_token(db, creds.credentials)


def current_user(user: User = Depends(authenticated_user), db: Session = Depends(get_db)) -> User:
    if user.must_change_password:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Password change required")
    now = utcnow()
    if user.last_seen_at is None or (now - user.last_seen_at).total_seconds() > 60:
        user.last_seen_at = now
        db.commit()
    return user


def require_roles(*roles: str):
    def checker(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
        return user
    return checker


require_staff = require_roles(*Role.STAFF)
require_admin = require_roles(Role.ADMIN)
require_head_or_admin = require_roles(Role.UNIT_HEAD, Role.ADMIN)


# Signed, expiring download URLs for private attachments.
def sign_file(attachment_id: int, viewer: User, expires: int | None = None) -> tuple[int, str]:
    expires = expires or int(time.time()) + get_settings().signed_url_seconds
    msg = f"{attachment_id}:{viewer.id}:{viewer.session_version}:{expires}".encode()
    return expires, hmac.new(get_settings().secret_key.encode(), msg, hashlib.sha256).hexdigest()


def verify_file_signature(attachment_id: int, viewer: User, expires: int, sig: str) -> bool:
    if expires < time.time():
        return False
    _, expected = sign_file(attachment_id, viewer, expires)
    return hmac.compare_digest(expected, sig)


# Signed, expiring download URLs for report exports (US17).
def sign_export(job_id: int, viewer: User, expires: int | None = None) -> tuple[int, str]:
    expires = expires or int(time.time()) + get_settings().export_link_hours * 3600
    msg = f"export:{job_id}:{viewer.id}:{viewer.session_version}:{expires}".encode()
    return expires, hmac.new(get_settings().secret_key.encode(), msg, hashlib.sha256).hexdigest()


def verify_export_signature(job_id: int, viewer: User, expires: int, sig: str) -> bool:
    if expires < time.time():
        return False
    _, expected = sign_export(job_id, viewer, expires)
    return hmac.compare_digest(expected, sig)
