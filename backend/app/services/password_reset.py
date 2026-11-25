from sqlalchemy.orm import Session

from ..db import utcnow
from ..models import EmailOutbox, PasswordResetToken


def invalidate_password_resets(db: Session, user_id: int) -> None:
    now = utcnow()
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id,
                                        PasswordResetToken.used_at.is_(None)).update(
        {PasswordResetToken.used_at: now}, synchronize_session=False)
    db.query(EmailOutbox).filter(EmailOutbox.user_id == user_id,
                                 EmailOutbox.kind == "password_reset",
                                 EmailOutbox.status == "queued").update(
        {EmailOutbox.status: "failed", EmailOutbox.last_error: "superseded",
         EmailOutbox.next_attempt_at: None}, synchronize_session=False)
