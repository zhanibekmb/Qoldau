import pytest
from pydantic import ValidationError

from app.bootstrap import bootstrap
from app.config import Settings
from app.models import Request, Role, User
from app.security import verify_password


def test_production_rejects_insecure_defaults():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(environment="production", database_url="postgresql+psycopg://localhost/qoldau",
                 cors_origins=["https://qoldau.example.org"])
    with pytest.raises(ValidationError, match="PostgreSQL"):
        Settings(environment="production", secret_key="x" * 32,
                 database_url="sqlite:///local.db",
                 cors_origins=["https://qoldau.example.org"])
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(environment="production", secret_key="x" * 32,
                 database_url="postgresql+psycopg://localhost/qoldau",
                 cors_origins=["http://qoldau.example.org"])
    assert Settings(environment="production", secret_key="x" * 32,
                    database_url="postgresql+psycopg://localhost/qoldau",
                    cors_origins=["https://qoldau.example.org"]).environment == "production"


def test_readiness_checks_database(client):
    assert client.get("/api/ready").json() == {"status": "ready"}


def test_bootstrap_creates_only_first_admin(db):
    # The normal test fixture already has demo data; bootstrap must not add another copy.
    before_requests = db.query(Request).count()
    assert bootstrap("first.admin@example.org", "a-unique-long-password") is True
    assert bootstrap("first.admin@example.org", "a-unique-long-password") is False
    user = db.query(User).filter_by(email="first.admin@example.org").one()
    assert user.role == Role.ADMIN
    assert verify_password("a-unique-long-password", user.password_hash)
    assert db.query(Request).count() == before_requests
    with pytest.raises(ValueError, match="unique admin password"):
        bootstrap("another@example.org", "Qoldau123!")
