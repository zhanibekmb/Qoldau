from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db, utcnow
from ..models import User
from ..security import create_tokens, current_user, decode_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def user_out(u: User) -> schemas.UserOut:
    out = schemas.UserOut.model_validate(u)
    out.unit_name = u.unit.name if u.unit else None
    return out


@router.post("/login", response_model=schemas.TokenOut)
def login(body: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    user.last_seen_at = utcnow()
    db.commit()
    return create_tokens(user)


@router.post("/refresh", response_model=schemas.TokenOut)
def refresh(body: schemas.RefreshIn, db: Session = Depends(get_db)):
    user = db.get(User, decode_token(body.refresh_token, "refresh"))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User inactive or not found")
    return create_tokens(user)


@router.get("/me", response_model=schemas.UserOut)
def me(user: User = Depends(current_user)):
    return user_out(user)


@router.post("/logout", status_code=204)
def logout(user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.last_seen_at = None  # no longer considered online for routing
    db.commit()
