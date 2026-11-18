"""Rate limits must count failed attempts and isolate authenticated users."""

from fastapi import Request

from app.config import get_settings
from conftest import DEMO_PASSWORD, login

API = "/api/v1"


def test_login_account_limit_counts_failed_attempts(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_login_account_per_minute", 2)
    body = {"email": "student@qoldau.edu.kz", "password": "wrong"}
    assert client.post(f"{API}/auth/login", json=body).status_code == 401
    assert client.post(f"{API}/auth/login", json=body).status_code == 401
    blocked = client.post(f"{API}/auth/login", json={**body, "password": DEMO_PASSWORD})
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0


def test_login_ip_limit_is_separate_from_account_limit(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_login_ip_per_minute", 2)
    for email in ("one@example.org", "two@example.org"):
        assert client.post(f"{API}/auth/login", json={"email": email, "password": "wrong"}).status_code == 401
    blocked = client.post(f"{API}/auth/login", headers={"Origin": "http://localhost:3000"},
                          json={"email": "three@example.org", "password": "wrong"})
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    assert blocked.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"


def test_ai_limit_uses_user_identity(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_ai_per_minute", 2)
    student = login(client, "student@qoldau.edu.kz")
    agent = login(client, "agent1.it@qoldau.edu.kz")
    body = {"subject": "Wi-Fi", "description": "My university email account is locked"}
    for _ in range(2):
        assert client.post(f"{API}/ai/classify", headers=student, json=body).status_code == 200
    blocked = client.post(f"{API}/ai/classify", headers=student, json=body)
    assert blocked.status_code == 429
    assert client.post(f"{API}/ai/classify", headers=agent, json=body).status_code == 200


def test_forwarded_ip_is_used_only_for_trusted_proxy():
    def request(peer):
        return Request({"type": "http", "method": "GET", "path": "/", "query_string": b"",
                        "headers": [(b"x-forwarded-for", b"203.0.113.6, 10.0.0.3")],
                        "client": (peer, 1234), "server": ("localhost", 8000), "scheme": "http"})

    from app.rate_limit import client_ip

    assert client_ip(request("198.51.100.20"), ["10.0.0.0/8"]) == "198.51.100.20"
    assert client_ip(request("10.0.0.4"), ["10.0.0.0/8"]) == "203.0.113.6"
