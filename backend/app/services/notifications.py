"""Persist in-app notifications and email outbox entries in the same transaction."""

from sqlalchemy import event
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import utcnow
from ..models import EmailOutbox, Notification, Request, User
from .realtime import hub

EMAIL_COPY = {
    "en": ("Qoldau update", "You have an update in Qoldau. Sign in to the portal to view it."),
    "ru": ("Обновление в Qoldau", "В Qoldau есть обновление. Войдите в портал, чтобы его посмотреть."),
    "kz": ("Qoldau порталындағы жаңарту", "Qoldau порталында жаңарту бар. Оны көру үшін порталға кіріңіз."),
}
PASSWORD_RESET_COPY = {
    "en": ("Reset your Qoldau password", "Use this one-time link to choose a new password. It expires in 15 minutes.\n\n{{RESET_URL}}\n\nIf you did not request this, ignore this email."),
    "ru": ("Сброс пароля Qoldau", "Перейдите по одноразовой ссылке, чтобы задать новый пароль. Ссылка действует 15 минут.\n\n{{RESET_URL}}\n\nЕсли вы не запрашивали сброс, просто проигнорируйте это письмо."),
    "kz": ("Qoldau құпиясөзін қалпына келтіру", "Жаңа құпиясөз орнату үшін бір реттік сілтемені ашыңыз. Сілтеме 15 минут жарамды.\n\n{{RESET_URL}}\n\nЕгер сұрауды сіз жасамаған болсаңыз, бұл хатты елемеңіз."),
}


def queue_push(db: Session, channel: str, payload: dict) -> None:
    db.info.setdefault("pushes", []).append((channel, payload))


@event.listens_for(Session, "after_commit")
def _flush_pushes(session: Session) -> None:
    for channel, payload in session.info.pop("pushes", []):
        hub.publish(channel, payload)


@event.listens_for(Session, "after_rollback")
def _drop_pushes(session: Session) -> None:
    session.info.pop("pushes", None)


def queue_email(db: Session, user: User, *, subject: str | None = None, body: str | None = None,
                include_portal_url: bool = True, kind: str = "notification") -> None:
    s = get_settings()
    default_subject, default_body = EMAIL_COPY.get(user.language, EMAIL_COPY["en"])
    subject = subject or default_subject
    body = body or default_body
    if include_portal_url and s.email_portal_url:
        body += f"\n\n{s.email_portal_url}\n"
    db.add(EmailOutbox(user_id=user.id, kind=kind, to=user.email, subject=subject, body=body,
                       status="queued" if s.smtp_host else "logged",
                       next_attempt_at=utcnow() if s.smtp_host else None))


def queue_password_reset_email(db: Session, user: User) -> None:
    subject, body = PASSWORD_RESET_COPY.get(user.language, PASSWORD_RESET_COPY["en"])
    queue_email(db, user, subject=subject, body=body, include_portal_url=False, kind="password_reset")


def notify(db: Session, user: User, type_: str, title: str, body: str = "", request: Request | None = None,
           email: bool = True) -> Notification:
    n = Notification(user_id=user.id, request_id=request.id if request else None, type=type_, title=title, body=body)
    db.add(n)
    db.flush()
    queue_push(db, f"user:{user.id}", {
        "event": "notification",
        "notification": {"id": n.id, "type": type_, "title": title, "body": body,
                         "request_id": n.request_id, "is_read": False,
                         "created_at": n.created_at.isoformat() + "Z"},
    })
    if email and user.is_active and user.email:
        queue_email(db, user)
    return n
