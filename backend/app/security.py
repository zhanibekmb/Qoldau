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


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def _token(user: User, kind: str, ttl: timedelta) -> str:
    now = int(time.time())
    payload = {"sub": str(user.id), "role": user.role, "type": kind, "iat": now, "exp": now + int(ttl.total_seconds())}
    return jwt.encode(payload, get_settings().secret_key, algorithm="HS256")


def create_tokens(user: User) -> dict:
    s = get_settings()
    return {
        "access_token": _token(user, "access", timedelta(minutes=s.access_token_minutes)),
        "refresh_token": _token(user, "refresh", timedelta(days=s.refresh_token_days)),
        "token_type": "bearer",
    }


def decode_token(token: str, kind: str) -> int:
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    if payload.get("type") != kind:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong token type")
    return int(payload["sub"])


def user_from_token(db: Session, token: str) -> User:
    user = db.get(User, decode_token(token, "access"))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User inactive or not found")
    return user


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user = user_from_token(db, creds.credentials)
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
def sign_file(attachment_id: int, user_id: int, expires: int | None = None) -> tuple[int, str]:
    expires = expires or int(time.time()) + get_settings().signed_url_seconds
    msg = f"{attachment_id}:{user_id}:{expires}".encode()
    return expires, hmac.new(get_settings().secret_key.encode(), msg, hashlib.sha256).hexdigest()


def verify_file_signature(attachment_id: int, user_id: int, expires: int, sig: str) -> bool:
    if expires < time.time():
        return False
    _, expected = sign_file(attachment_id, user_id, expires)
    return hmac.compare_digest(expected, sig)


# Signed, expiring download URLs for report exports (US17).
def sign_export(job_id: int, user_id: int, expires: int | None = None) -> tuple[int, str]:
    expires = expires or int(time.time()) + get_settings().export_link_hours * 3600
    msg = f"export:{job_id}:{user_id}:{expires}".encode()
    return expires, hmac.new(get_settings().secret_key.encode(), msg, hashlib.sha256).hexdigest()


def verify_export_signature(job_id: int, user_id: int, expires: int, sig: str) -> bool:
    if expires < time.time():
        return False
    _, expected = sign_export(job_id, user_id, expires)
    return hmac.compare_digest(expected, sig)
