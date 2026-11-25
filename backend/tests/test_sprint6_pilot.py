import smtplib
import socketserver
import struct
import threading
from datetime import timedelta

import pytest
from starlette.websockets import WebSocketDisconnect

from app.config import Settings, get_settings
from app.db import utcnow
from app.models import Attachment, ContentEmbedding, EmailOutbox, ReportJob, Request, SLAPolicy, Status, User
from app.pilot_retention import purge_report, purge_request
from app.services import email_delivery, file_scan, notifications, sla
from conftest import login

API = "/api/v1"
STUDENT = "student@qoldau.edu.kz"
ADMIN = "admin@qoldau.edu.kz"
AGENT = "agent1.it@qoldau.edu.kz"
TEMP = "Local-test-password-one!"
NEW = "Local-test-password-two!"


def _login(client, email, password):
    res = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()


def _header(pair):
    return {"Authorization": f"Bearer {pair['access_token']}"}


def test_logout_revokes_access_and_refresh_tokens(client):
    pair = _login(client, STUDENT, "Qoldau123!")
    headers = _header(pair)

    assert client.post(f"{API}/auth/logout", headers=headers).status_code == 204
    assert client.get(f"{API}/auth/me", headers=headers).status_code == 401
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": pair["refresh_token"]}).status_code == 401


def _submit(client, headers):
    res = client.post(f"{API}/requests", headers=headers, json={"subject": "Private campus Wi-Fi problem",
                      "description": "My campus Wi-Fi does not connect and the university email account is locked."})
    assert res.status_code == 201, res.text
    assert res.json()["unit"]["name"] == "IT Help Desk"
    return res.json()["id"]


@pytest.mark.parametrize("role", ["student", "agent"])
def test_pilot_issuance_and_recovery(client, db, role):
    admin = login(client, ADMIN)
    email = f"pilot-{role}@example.org"
    it_unit = db.query(User).filter_by(email=AGENT).one().unit_id
    account = {"name": "Pilot Account", "email": email, "role": role,
               "unit_id": it_unit if role == "agent" else None, "password": TEMP}
    res = client.post(f"{API}/admin/users", headers=admin, json=account)
    assert res.status_code == 201, res.text
    user_id = res.json()["id"]
    assert res.json()["must_change_password"] is True

    initial = _login(client, email, TEMP)
    assert client.get(f"{API}/auth/me", headers=_header(initial)).json()["must_change_password"]
    assert client.get(f"{API}/requests", headers=_header(initial)).status_code == 403
    with pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect(f"/ws/notifications?token={initial['access_token']}"):
            pytest.fail("Temporary password session connected")
    assert closed.value.code == 4401

    changed = client.post(f"{API}/auth/change-password", headers=_header(initial),
                          json={"current_password": TEMP, "new_password": NEW})
    assert changed.status_code == 200, changed.text
    pair = changed.json()
    headers = _header(pair)
    assert client.get(f"{API}/auth/me", headers=headers).json()["must_change_password"] is False
    assert client.get(f"{API}/requests", headers=headers).status_code == 200
    assert client.get(f"{API}/meta/agents", headers=headers).status_code == (403 if role == "student" else 200)
    if role == "student":
        someone_elses = _submit(client, login(client, STUDENT))
        assert client.get(f"{API}/requests/{someone_elses}", headers=headers).status_code == 404
    assert client.get(f"{API}/auth/me", headers=_header(initial)).status_code == 401
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": initial["refresh_token"]}).status_code == 401
    assert client.post(f"{API}/auth/login", json={"email": email, "password": TEMP}).status_code == 401

    with client.websocket_connect(f"/ws/notifications?token={pair['access_token']}") as ws:
        ws.send_text("ping")
        assert ws.receive_json()["event"] == "pong"
        assert client.put(f"{API}/admin/users/{user_id}", headers=admin, json=account).status_code == 200
        ws.send_text("ping")
        with pytest.raises(WebSocketDisconnect) as revoked:
            ws.receive_text()
        assert revoked.value.code == 4401
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": pair["refresh_token"]}).status_code == 401
    reset = _login(client, email, TEMP)
    assert client.get(f"{API}/auth/me", headers=_header(reset)).json()["must_change_password"] is True

    account.update(password=None, is_active=False)
    assert client.put(f"{API}/admin/users/{user_id}", headers=admin, json=account).status_code == 200
    account.update(is_active=True)
    assert client.put(f"{API}/admin/users/{user_id}", headers=admin, json=account).status_code == 200
    assert client.get(f"{API}/auth/me", headers=_header(reset)).status_code == 401


def test_public_sla_uses_live_policy_and_demo_requires_opt_in(client, db, monkeypatch):
    settings = get_settings()
    assert client.get(f"{API}/auth/demo").status_code == 404
    assert client.get(f"{API}/meta/public").json()["sla"] == []
    monkeypatch.setattr(settings, "demo_login_enabled", True)
    assert client.get(f"{API}/auth/demo").headers["cache-control"] == "no-store"
    monkeypatch.setattr(settings, "environment", "production")
    assert client.get(f"{API}/auth/demo").status_code == 404
    assert client.get(f"{API}/meta/public").json()["attachments_enabled"] is False

    monkeypatch.setattr(settings, "pilot_directory_published", True)
    policy = db.query(SLAPolicy).filter_by(priority="High").one()
    policy.first_response_hours, policy.use_working_hours = 7.5, True
    db.commit()
    service = client.get(f"{API}/meta/public").json()
    row = next(row for row in service["sla"] if row["priority"] == "High")
    assert (row["first_response_hours"], row["resolution_hours"], row["use_working_hours"]) == sla.policy_for(db, "High")
    assert sum(unit["is_triage"] for unit in service["offices"]) == 1
    assert all("head_user_id" not in unit for unit in service["offices"])
    assert Settings().demo_login_enabled is False


def test_smtp_retry_privacy_and_escalation(client, db, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "smtp_host", "")
    student = login(client, STUDENT)
    request_id = _submit(client, student)
    agent = login(client, AGENT)
    db.query(User).filter_by(email=STUDENT).one().email = "pilot.student@sdu.edu.kz"
    db.query(User).filter_by(email=AGENT).one().email = "pilot.agent@sdu.edu.kz"
    db.query(User).filter_by(email="head.it@qoldau.edu.kz").one().email = "pilot.head@sdu.edu.kz"
    db.commit()
    monkeypatch.setattr(settings, "smtp_host", "relay.test")
    monkeypatch.setattr(settings, "smtp_user", "")
    monkeypatch.setattr(settings, "smtp_password", "")
    monkeypatch.setattr(settings, "email_portal_url", "https://portal.example.org/login")
    monkeypatch.setattr(settings, "smtp_from", "qoldau@example.org")
    replies = iter((451, 0, 550))
    messages = []

    class LocalSMTP:
        def __init__(self, *args, **kwargs):
            self.tls = False

        def starttls(self, *, context):
            self.tls = context.check_hostname

        def send_message(self, msg):
            assert self.tls
            messages.append(msg)
            code = next(replies, 0)
            if code:
                raise smtplib.SMTPDataError(code, b"private relay response")

        def close(self):
            pass

    monkeypatch.setattr(email_delivery.smtplib, "SMTP", LocalSMTP)
    path = f"{API}/requests/{request_id}/messages"
    assert client.post(path, headers=agent, json={"body": "A private staff reply"}).status_code == 201
    assert client.post(path, headers=agent, json={"body": "A private internal note", "is_internal": True}).status_code == 201
    db.expire_all()
    pending = db.query(EmailOutbox).filter_by(status="queued").one()
    assert pending.to == "pilot.student@sdu.edu.kz"
    email_delivery.deliver_job()
    db.refresh(pending)
    assert (pending.status, pending.last_error, pending.attempts) == ("queued", "smtp_451", 1)
    assert pending.next_attempt_at > utcnow()
    pending.next_attempt_at = utcnow() - timedelta(seconds=1)
    db.commit()
    email_delivery.deliver_job()
    db.refresh(pending)
    assert pending.status == "sent" and pending.attempts == 2 and pending.sent_at
    assert messages[0]["Message-ID"] == messages[1]["Message-ID"]
    assert any(n["type"] == "reply" for n in client.get(f"{API}/notifications", headers=student).json())

    req = db.get(Request, request_id)
    req.first_response_at = None
    req.sla_first_response_due = utcnow() - timedelta(minutes=1)
    db.commit()
    sla.run_tick(db)
    email_delivery.deliver_job()
    db.expire_all()
    failure = db.query(EmailOutbox).filter_by(status="failed", last_error="smtp_550").one()
    assert failure.attempts == 1 and failure.last_error == "smtp_550" and failure.next_attempt_at is None
    assert any(str(m["To"]) == "pilot.head@sdu.edu.kz" for m in messages)
    for msg in messages:
        assert "https://portal.example.org/login" in msg.get_content()
        assert all(secret not in msg.as_string() for secret in (request_id, "Private campus", "private internal", "private staff"))


def test_smtp_reclaims_expired_delivery_lease(db, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "smtp_host", "relay.test")
    monkeypatch.setattr(settings, "email_portal_url", "https://portal.example.org/login")
    user = db.query(User).filter_by(email=STUDENT).one()
    user.email = "pilot.student@sdu.edu.kz"
    notifications.queue_email(db, user)
    db.commit()
    claim = email_delivery._claim(settings)
    assert claim.status == "sending" and claim.attempts == 1
    assert email_delivery._claim(settings) is None
    row = db.get(EmailOutbox, claim.id)
    row.next_attempt_at = utcnow() - timedelta(seconds=1)
    db.commit()

    sent = []
    monkeypatch.setattr(email_delivery, "_send", lambda message, _: sent.append(message.id))
    email_delivery.deliver_job()
    db.refresh(row)
    assert sent == [row.id]
    assert row.status == "sent" and row.attempts == 2 and row.claim_id is None


def test_smtp_delivery_only_sends_to_active_sdu_accounts(db, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "smtp_host", "relay.test")
    monkeypatch.setattr(settings, "email_portal_url", "https://portal.example.org/login")
    sent = []
    monkeypatch.setattr(email_delivery, "_send", lambda row, _: sent.append(row.to))

    approved = db.query(User).filter_by(email=STUDENT).one()
    approved.email = "pilot.student@sdu.edu.kz"
    demo = db.query(User).filter_by(email="student2@qoldau.edu.kz").one()
    notifications.queue_email(db, approved)
    notifications.queue_email(db, demo)
    db.commit()

    email_delivery.deliver_job(limit=20)
    db.expire_all()
    approved_mail = db.query(EmailOutbox).filter_by(to="pilot.student@sdu.edu.kz").one()
    demo_mail = db.query(EmailOutbox).filter_by(to="student2@qoldau.edu.kz").one()
    assert sent == ["pilot.student@sdu.edu.kz"]
    assert approved_mail.status == "sent"
    assert demo_mail.status == "failed" and demo_mail.last_error == "recipient_not_approved"


def test_attachment_verdict_and_access(client, db, monkeypatch, tmp_path):
    class ClamdStub(socketserver.StreamRequestHandler):
        def handle(self):
            assert self.rfile.read(10) == b"zINSTREAM\0"
            payload = bytearray()
            while size := struct.unpack(">I", self.rfile.read(4))[0]:
                payload.extend(self.rfile.read(size))
            self.wfile.write(b"stream: Test FOUND\0" if file_scan.EICAR in payload else b"stream: OK\0")

    settings = get_settings()
    monkeypatch.setattr(settings, "attachment_mode", "clamav")
    monkeypatch.setattr(settings, "clamav_host", "127.0.0.1")
    monkeypatch.setattr(settings, "upload_dir", tmp_path)
    student = login(client, STUDENT)
    req_id = _submit(client, student)
    url = f"{API}/requests/{req_id}/attachments"
    def files(payload):
        return {"file": ("example.pdf", payload, "application/pdf")}

    with socketserver.TCPServer(("127.0.0.1", 0), ClamdStub) as server:
        monkeypatch.setattr(settings, "clamav_port", server.server_address[1])
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            uploaded = client.post(url, headers=student, files=files(b"%PDF test"))
            assert uploaded.status_code == 201, uploaded.text
            assert client.post(url, headers=student, files=files(b"%PDF " + file_scan.EICAR)).status_code == 422
        finally:
            server.shutdown()
            worker.join()

    assert client.post(url, headers=student, files=files(b"%PDF test")).status_code == 503
    attachment = uploaded.json()
    path = f"{API}/requests/{req_id}/messages"
    assert client.post(path, headers=student, json={"body": "", "attachment_ids": [attachment["id"]]}).status_code == 201
    assert client.get(attachment["url"]).content == b"%PDF test"
    agent_copy = client.get(path, headers=login(client, AGENT)).json()[0]["attachments"][0]
    assert client.get(agent_copy["url"]).status_code == 200
    assert client.get(path, headers=login(client, "student2@qoldau.edu.kz")).status_code == 404
    assert db.query(Attachment).count() == 1

    monkeypatch.setattr(settings, "attachment_mode", "disabled")
    assert client.get(f"{API}/meta/public").json()["attachments_enabled"] is False
    assert client.post(url, headers=student, files=files(b"%PDF test")).status_code == 403
    assert client.get(attachment["url"]).status_code == 404


def test_retention_inspection_and_targeted_purge(client, db, monkeypatch, tmp_path):
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_dir", tmp_path / "uploads")
    monkeypatch.setattr(settings, "export_dir", tmp_path / "reports")
    student = login(client, STUDENT)
    case = _submit(client, student)
    other = _submit(client, student)
    attachment = client.post(f"{API}/requests/{case}/attachments", headers=student,
                             files={"file": ("sample.pdf", b"%PDF clean", "application/pdf")})
    assert attachment.status_code == 201
    req = db.get(Request, case)
    req.status, req.closed_at = Status.CLOSED, utcnow() - timedelta(days=10)
    db.add(ContentEmbedding(entity_type="request", entity_id=case, language="en", provider="test",
                            dim=1, vector=b"test", text_hash="test"))
    admin = db.query(User).filter_by(email=ADMIN).one()
    job = ReportJob(type="excel", status="done", file_key="test.xlsx", requested_by=admin.id, finished_at=req.closed_at)
    settings.export_dir.mkdir()
    (settings.export_dir / "test.xlsx").write_bytes(b"test")
    db.add(job)
    db.commit()

    cutoff = utcnow() - timedelta(days=5)
    with pytest.raises(ValueError, match="still running|open"):
        purge_request(db, other, cutoff, apply=True)
    assert purge_request(db, case, cutoff)["attachment_files"] == 1
    assert purge_report(db, job.id, cutoff)["file_found"] is True
    assert purge_request(db, case, cutoff, apply=True)["applied"] is True
    assert purge_request(db, case, cutoff, apply=True)["attachment_files"] == 0
    assert purge_report(db, job.id, cutoff, apply=True)["applied"] is True
    assert client.get(f"{API}/requests/{case}", headers=student).status_code == 404
    assert client.get(f"{API}/requests/{other}", headers=student).status_code == 200
    assert db.query(ContentEmbedding).filter_by(entity_id=case).count() == 0
    assert db.query(Attachment).filter_by(request_id=case).count() == 0
    assert not (settings.upload_dir / case).exists()
    assert not (settings.export_dir / "test.xlsx").exists()
