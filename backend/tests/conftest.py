import os
import random
import sys
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="qoldau-test-"))
os.environ["QOLDAU_DATABASE_URL"] = f"sqlite:///{(_tmp / 'test.db').as_posix()}"
os.environ["QOLDAU_SCHEDULER_ENABLED"] = "false"
os.environ["QOLDAU_UPLOAD_DIR"] = str(_tmp / "uploads")
os.environ["QOLDAU_EXPORT_DIR"] = str(_tmp / "exports")
os.environ["QOLDAU_MODEL_DIR"] = str(_tmp / "models")  # retraining writes versioned artifacts here
os.environ["QOLDAU_JOBS_INLINE"] = "true"  # background jobs run right after commit
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine, utcnow  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.seed import DEMO_PASSWORD, seed_reference, seed_users  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    s = SessionLocal()
    units = seed_reference(s)
    seed_users(s, units, random.Random(1))
    s.commit()
    yield s
    s.close()


@pytest.fixture()
def client(db):
    with TestClient(app) as c:
        yield c


def login(client: TestClient, email: str) -> dict:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def set_online(db, *emails: str, online: bool = True) -> None:
    for e in emails:
        u = db.query(User).filter_by(email=e).one()
        u.last_seen_at = utcnow() if online else None
    db.commit()


def set_offline_unit(db, unit_slug: str) -> None:
    for u in db.query(User).filter(User.email.like(f"%.{unit_slug}@qoldau.edu.kz")):
        u.last_seen_at = None
    db.commit()
