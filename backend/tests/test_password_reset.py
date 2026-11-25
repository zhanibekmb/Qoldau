import hashlib
import re
from datetime import timedelta

from app.config import get_settings
from app.db import utcnow
from app.models import EmailOutbox, PasswordResetToken, User
from app.services import email_delivery

API = "/api/v1/auth"
EMAIL = "student@qoldau.edu.kz"
PASSWORD = "Qoldau123!"


def _pair(client, email, password):
    response = client.post(f"{API}/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def _request(client, email):
    return client.post(f"{API}/password-reset/request", json={"email": email})


def test_reset_email_is_generic_sdu_only_and_token_is_issued_on_delivery(client, db, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "smtp_host", "relay.test")
    monkeypatch.setattr(settings, "email_portal_url", "http://127.0.0.1:18435/login")
    monkeypatch.setattr(settings, "smtp_user", "")
    monkeypatch.setattr(settings, "smtp_password", "")
    sent_bodies = []
    monkeypatch.setattr(email_delivery, "_send", lambda row, _, body=None: sent_bodies.append(body or row.body))

    user = db.query(User).filter_by(email=EMAIL).one()
    user.email = "reset.student@sdu.edu.kz"
    db.commit()

    eligible = _request(client, user.email)
    unknown = _request(client, "nobody@sdu.edu.kz")
    demo = _request(client, EMAIL)
    assert eligible.status_code == unknown.status_code == demo.status_code == 202
    assert eligible.json() == unknown.json() == demo.json()
    queued = db.query(EmailOutbox).filter_by(user_id=user.id, kind="password_reset").one()
    assert queued.status == "queued" and "{{RESET_URL}}" in queued.body
    assert db.query(PasswordResetToken).count() == 0
    assert db.query(EmailOutbox).filter_by(to=EMAIL, kind="password_reset").count() == 0

    email_delivery.deliver_job(limit=5)
    db.refresh(queued)
    assert queued.status == "sent" and queued.attempts == 1
    assert db.query(PasswordResetToken).count() == 1
    match = re.search(r"/reset-password\?token=([A-Za-z0-9_-]+)", sent_bodies[0])
    assert match
    raw_token = match.group(1)
    stored = db.query(PasswordResetToken).one()
    assert stored.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
    assert raw_token not in stored.token_hash and raw_token not in queued.body
    assert stored.expires_at - stored.created_at == timedelta(minutes=15)


def test_reset_is_one_time_revokes_sessions_and_accepts_new_password(client, db, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "smtp_host", "relay.test")
    monkeypatch.setattr(settings, "email_portal_url", "http://127.0.0.1:18435/login")
    monkeypatch.setattr(settings, "smtp_user", "")
    monkeypatch.setattr(settings, "smtp_password", "")
    sent_bodies = []
    monkeypatch.setattr(email_delivery, "_send", lambda row, _, body=None: sent_bodies.append(body or row.body))

    user = db.query(User).filter_by(email=EMAIL).one()
    user.email = "reset.student@sdu.edu.kz"
    db.commit()
    old = _pair(client, user.email, PASSWORD)
    assert _request(client, user.email).status_code == 202
    email_delivery.deliver_job(limit=1)
    token = re.search(r"/reset-password\?token=([A-Za-z0-9_-]+)", sent_bodies[0]).group(1)
    new_password = "New-SDU-password-2026!"
    body = {"token": token, "new_password": new_password, "confirm_password": new_password}

    reset = client.post(f"{API}/password-reset/confirm", json=body)
    assert reset.status_code == 200
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old['access_token']}"}).status_code == 401
    assert client.post(f"{API}/refresh", json={"refresh_token": old["refresh_token"]}).status_code == 401
    assert client.post(f"{API}/password-reset/confirm", json=body).status_code == 400
    assert client.post(f"{API}/login", json={"email": user.email, "password": new_password}).status_code == 200
    assert client.post(f"{API}/login", json={"email": user.email, "password": PASSWORD}).status_code == 401


def test_reset_expiry_and_rate_limit(client, db, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "smtp_host", "relay.test")
    user = db.query(User).filter_by(email=EMAIL).one()
    user.email = "reset.student@sdu.edu.kz"
    db.commit()

    for _ in range(4):
        response = _request(client, user.email)
        assert response.status_code == 202
        assert response.json() == {"message": "If an active SDU account exists for this address, a reset link will be sent."}
    assert db.query(EmailOutbox).filter_by(user_id=user.id, kind="password_reset").count() == 3

    expired = "x" * 43
    db.add(PasswordResetToken(user_id=user.id, token_hash=hashlib.sha256(expired.encode()).hexdigest(),
                              created_at=utcnow() - timedelta(minutes=16),
                              expires_at=utcnow() - timedelta(minutes=1)))
    db.commit()
    result = client.post(f"{API}/password-reset/confirm", json={
        "token": expired, "new_password": "A-new-password-2026!", "confirm_password": "A-new-password-2026!",
    })
    assert result.status_code == 400
