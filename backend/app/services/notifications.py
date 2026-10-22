"""In-app + email notifications (US8).

Realtime pushes and emails are queued on the DB session and only dispatched after the
transaction commits, so clients never receive events for data that was rolled back.
"""
import logging
import smtplib
import threading
from email.message import EmailMessage

from sqlalchemy import event
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import EmailOutbox, Notification, Request, User
from .realtime import hub

log = logging.getLogger(__name__)


def queue_push(db: Session, channel: str, payload: dict) -> None:
    db.info.setdefault("pushes", []).append((channel, payload))


@event.listens_for(Session, "after_commit")
def _flush_pushes(session: Session) -> None:
    pushes = session.info.pop("pushes", [])
    emails = session.info.pop("emails", [])
    for channel, payload in pushes:
        hub.publish(channel, payload)
    if emails:
        threading.Thread(target=_send_emails, args=(emails,), daemon=True).start()


@event.listens_for(Session, "after_rollback")
def _drop_pushes(session: Session) -> None:
    session.info.pop("pushes", None)
    session.info.pop("emails", None)


def _send_emails(emails: list[tuple[str, str, str]]) -> None:
    s = get_settings()
    if not s.smtp_host:
        for to, subject, _ in emails:
            log.info("email (logged only) to=%s subject=%s", to, subject)
        return
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if s.smtp_user:
                smtp.login(s.smtp_user, s.smtp_password)
            for to, subject, body in emails:
                msg = EmailMessage()
                msg["From"], msg["To"], msg["Subject"] = s.smtp_from, to, subject
                msg.set_content(body)
                smtp.send_message(msg)
    except Exception:
        log.exception("SMTP delivery failed")


def send_email(db: Session, to: str, subject: str, body: str) -> None:
    db.add(EmailOutbox(to=to, subject=subject, body=body, status="queued" if get_settings().smtp_host else "logged"))
    db.info.setdefault("emails", []).append((to, subject, body))


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
    if email and user.email:
        ref = f"[{request.id}] " if request else ""
        lines = [body]
        if request:
            lines += ["", f"Request: {request.id}", f"Subject: {request.subject}", f"Status: {request.status}"]
        send_email(db, user.email, f"{ref}{title}", "\n".join(lines))
    return n
