import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db, utcnow
from ..models import PasswordResetToken, Role, User
from ..config import get_settings
from ..rate_limit import RateLimitExceeded, client_ip, enforce_limit
from ..security import authenticated_user, create_tokens, hash_new_password, user_from_token, verify_password
from ..services.notifications import queue_password_reset_email
from ..services.password_reset import invalidate_password_resets

router = APIRouter(prefix="/auth", tags=["auth"])
RESET_ACCEPTED = {"message": "If an active SDU account exists for this address, a reset link will be sent."}
RESET_INVALID = "Reset link is invalid or expired"


def _is_sdu_email(email: str) -> bool:
    return email.rpartition("@")[2].casefold() == "sdu.edu.kz"


def user_out(u: User) -> schemas.UserOut:
    out = schemas.UserOut.model_validate(u)
    out.unit_name = u.unit.name if u.unit else None
    return out


@router.get("/demo", include_in_schema=False)
def demo_login(response: Response):
    settings = get_settings()
    if settings.environment != "development" or not settings.demo_login_enabled:
        return Response(status_code=404, headers={"Cache-Control": "no-store"})
    from ..seed import DEMO_PASSWORD

    response.headers["Cache-Control"] = "no-store"
    return {"password": DEMO_PASSWORD, "accounts": [
        {"role": Role.STUDENT, "email": "student@qoldau.edu.kz"},
        {"role": Role.AGENT, "email": "agent1.it@qoldau.edu.kz"},
        {"role": Role.AGENT, "email": "agent1.triage@qoldau.edu.kz", "triage": True},
        {"role": Role.UNIT_HEAD, "email": "head.library@qoldau.edu.kz"},
        {"role": Role.ADMIN, "email": "admin@qoldau.edu.kz"},
    ]}


@router.post("/login", response_model=schemas.TokenOut)
def login(body: schemas.LoginIn, db: Session = Depends(get_db)):
    settings = get_settings()
    if settings.rate_limits_enabled:
        try:
            enforce_limit("login-account", body.email.lower(), settings.rate_limit_login_account_per_minute, 60)
        except RateLimitExceeded as exc:
            raise HTTPException(429, "Rate limit exceeded", headers={"Retry-After": str(exc.retry_after)})
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.must_change_password:
        user.last_seen_at = utcnow()
    db.commit()
    return create_tokens(user)


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(body: schemas.PasswordResetRequestIn, request: Request, response: Response,
                           db: Session = Depends(get_db)):
    settings = get_settings()
    response.headers["Cache-Control"] = "no-store"
    email = str(body.email).strip().casefold()
    if settings.rate_limits_enabled:
        try:
            enforce_limit("password-reset-ip", client_ip(request, settings.trusted_proxy_cidrs), 10, 3600)
            enforce_limit("password-reset-email", email, 3, 3600)
        except RateLimitExceeded:
            return RESET_ACCEPTED

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active or not _is_sdu_email(user.email) or not settings.smtp_host:
        return RESET_ACCEPTED

    invalidate_password_resets(db, user.id)
    queue_password_reset_email(db, user)
    db.commit()
    return RESET_ACCEPTED


@router.post("/password-reset/confirm")
def confirm_password_reset(body: schemas.PasswordResetConfirmIn, db: Session = Depends(get_db)):
    now = utcnow()
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    reset = db.query(PasswordResetToken).filter_by(token_hash=token_hash).first()
    if not reset or reset.used_at is not None or reset.expires_at <= now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, RESET_INVALID)
    user = db.get(User, reset.user_id)
    if not user or not user.is_active or not _is_sdu_email(user.email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, RESET_INVALID)

    claimed = db.execute(update(PasswordResetToken).where(
        PasswordResetToken.id == reset.id, PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > now).values(used_at=now))
    if claimed.rowcount != 1:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, RESET_INVALID)
    changed = db.execute(update(User).where(User.id == user.id, User.is_active.is_(True),
                                            User.session_version == user.session_version).values(
        password_hash=hash_new_password(body.new_password), must_change_password=False,
        session_version=User.session_version + 1, last_seen_at=None))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, RESET_INVALID)
    invalidate_password_resets(db, user.id)
    db.commit()
    return {"message": "Password reset successfully"}


@router.post("/refresh", response_model=schemas.TokenOut)
def refresh(body: schemas.RefreshIn, db: Session = Depends(get_db)):
    return create_tokens(user_from_token(db, body.refresh_token, "refresh"))


@router.get("/me", response_model=schemas.UserOut)
def me(response: Response, user: User = Depends(authenticated_user)):
    response.headers["Cache-Control"] = "private, no-store"
    return user_out(user)


@router.post("/change-password", response_model=schemas.TokenOut)
def change_password(body: schemas.ChangePasswordIn, db: Session = Depends(get_db),
                    user: User = Depends(authenticated_user)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(422, "Current password is incorrect")
    if body.current_password == body.new_password:
        raise HTTPException(422, "Choose a different password")
    changed = db.execute(update(User).where(User.id == user.id, User.session_version == user.session_version)
                         .values(password_hash=hash_new_password(body.new_password), must_change_password=False,
                                 session_version=User.session_version + 1, last_seen_at=utcnow()))
    if changed.rowcount != 1:
        raise HTTPException(409, "Account changed. Sign in again")
    invalidate_password_resets(db, user.id)
    db.refresh(user)
    tokens = create_tokens(user)
    db.commit()
    return tokens


@router.post("/logout", status_code=204)
def logout(user: User = Depends(authenticated_user), db: Session = Depends(get_db)):
    # Bump the version so both the current access token and its refresh token
    # stop working immediately, including tokens copied to another browser.
    user.session_version += 1
    user.last_seen_at = None  # no longer considered online for routing
    db.commit()
