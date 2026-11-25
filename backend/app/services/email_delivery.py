"""Retryable SMTP delivery using leases shared by application workers."""
import hashlib
import logging
import smtplib
import ssl
import secrets
import uuid
from contextlib import closing
from datetime import timedelta, timezone
from email.message import EmailMessage
from email.utils import formatdate
from urllib.parse import urlencode, urlsplit, urlunsplit

from sqlalchemy import select, update

from ..config import Settings, get_settings
from ..db import SessionLocal, utcnow
from ..models import EmailOutbox, PasswordResetToken, User

log = logging.getLogger(__name__)
LEASE = timedelta(minutes=10)
RESET_LIFETIME = timedelta(minutes=15)
RESET_MARKER = "{{RESET_URL}}"


def _send(row: EmailOutbox, settings: Settings, body: str | None = None) -> None:
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.smtp_from, row.to, row.subject
    msg["Date"] = formatdate(row.created_at.replace(tzinfo=timezone.utc).timestamp(), usegmt=True)
    msg["Message-ID"] = f"<qoldau.outbox.{row.id}@{urlsplit(settings.email_portal_url).hostname}>"
    msg.set_content(body if body is not None else row.body)
    context = ssl.create_default_context()
    if settings.smtp_security == "ssl":
        connection = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10, context=context)
    else:
        connection = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
    with closing(connection) as smtp:
        if settings.smtp_security == "starttls":
            smtp.starttls(context=context)
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


def _failure(exc: Exception) -> tuple[str, bool]:
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        code = next(iter(exc.recipients.values()))[0]
    elif isinstance(exc, smtplib.SMTPResponseException):
        code = exc.smtp_code
    elif isinstance(exc, (ssl.SSLCertVerificationError, smtplib.SMTPNotSupportedError)):
        return "tls_configuration", False
    elif isinstance(exc, OSError):
        return "smtp_unavailable", True
    else:
        return "invalid_message", False
    return f"smtp_{code}", 400 <= code < 500


def _claim(settings: Settings) -> EmailOutbox | None:
    now = utcnow()
    pending = (EmailOutbox.status.in_(("queued", "sending")), EmailOutbox.next_attempt_at <= now)
    with SessionLocal() as db:
        db.execute(update(EmailOutbox).where(*pending, EmailOutbox.attempts >= settings.email_max_attempts)
                   .values(status="failed", claim_id=None, next_attempt_at=None, last_error="attempts_exhausted"))
        row_id = db.scalar(select(EmailOutbox.id).where(*pending)
                           .order_by(EmailOutbox.next_attempt_at, EmailOutbox.id).limit(1))
        if row_id is None:
            db.commit()
            return None
        claim_id = uuid.uuid4().hex
        claimed = db.execute(update(EmailOutbox).where(EmailOutbox.id == row_id, *pending)
                             .values(status="sending", attempts=EmailOutbox.attempts + 1,
                                     claim_id=claim_id, next_attempt_at=now + LEASE))
        row = db.get(EmailOutbox, row_id) if claimed.rowcount == 1 else None
        db.commit()
        return row


def _reset_email_body(row: EmailOutbox, settings: Settings) -> tuple[str | None, str | None]:
    if RESET_MARKER not in row.body or not settings.email_portal_url:
        return None, None
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = utcnow()
    with SessionLocal() as db:
        user = db.get(User, row.user_id) if row.user_id is not None else None
        if not user or not user.is_active or user.email.casefold() != row.to.casefold() \
                or user.email.rpartition("@")[2].casefold() != "sdu.edu.kz":
            return None, None
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id,
                                            PasswordResetToken.used_at.is_(None)).update(
            {PasswordResetToken.used_at: now}, synchronize_session=False)
        db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, created_at=now,
                                  expires_at=now + RESET_LIFETIME))
        db.commit()

    portal = urlsplit(settings.email_portal_url)
    base = portal.path.rsplit("/", 1)[0] if portal.path else ""
    path = f"{base}/reset-password" if base else "/reset-password"
    link = urlunsplit((portal.scheme, portal.netloc, path, urlencode({"token": token}), ""))
    return row.body.replace(RESET_MARKER, link), token_hash


def _revoke_reset_token(token_hash: str) -> None:
    with SessionLocal() as db:
        db.query(PasswordResetToken).filter_by(token_hash=token_hash, used_at=None).update(
            {PasswordResetToken.used_at: utcnow()}, synchronize_session=False)
        db.commit()


def deliver_job(limit: int = 20) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        return
    for _ in range(limit):
        row = _claim(settings)
        if row is None:
            return
        with SessionLocal() as db:
            user = db.get(User, row.user_id) if row.user_id is not None else None
            allowed = bool(user and user.is_active and user.email.casefold() == row.to.casefold()
                           and user.email.rpartition("@")[2].casefold() == "sdu.edu.kz")

        now = utcnow()
        values = dict(status="sent", sent_at=now, last_error=None, next_attempt_at=None, claim_id=None)
        reset_token_hash = None
        if not allowed:
            values.update(status="failed", last_error="recipient_not_approved", sent_at=None)
        else:
            try:
                body = None
                if row.kind == "password_reset":
                    body, reset_token_hash = _reset_email_body(row, settings)
                    if body is None:
                        raise ValueError("reset_email_unavailable")
                _send(row, settings, body) if body is not None else _send(row, settings)
                values["sent_at"] = utcnow()
            except (OSError, ValueError) as exc:
                if reset_token_hash:
                    _revoke_reset_token(reset_token_hash)
                error, retry = _failure(exc)
                values.update(status="failed", last_error=error, sent_at=None)
                if retry and row.attempts < settings.email_max_attempts:
                    delay = min(60 * (2 ** (row.attempts - 1)), 3600)
                    values.update(status="queued", next_attempt_at=utcnow() + timedelta(seconds=delay))
        with SessionLocal() as db:
            db.execute(update(EmailOutbox).where(EmailOutbox.id == row.id, EmailOutbox.claim_id == row.claim_id)
                       .values(**values))
            db.commit()
        if values["status"] == "failed":
            log.warning("Email delivery failed outbox_id=%s code=%s", row.id, values["last_error"])
