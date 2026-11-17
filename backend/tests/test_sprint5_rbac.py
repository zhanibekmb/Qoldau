"""Access regressions for triage, cross-unit requests and signed attachments."""

import pytest
from fastapi import WebSocketDisconnect

from app.models import Request, Role, Status, Unit, User
from conftest import login

API = "/api/v1"


def submit(client, description: str):
    student = login(client, "student@qoldau.edu.kz")
    response = client.post(f"{API}/requests", headers=student,
                           json={"subject": "Help", "description": description})
    assert response.status_code == 201, response.text
    return response.json(), student


def test_only_triage_staff_can_access_unassigned_review_request(client, db):
    req, _ = submit(client, "help please!!")
    assert req["status"] == Status.NEEDS_REVIEW
    triage = login(client, "agent1.triage@qoldau.edu.kz")
    other = login(client, "agent1.it@qoldau.edu.kz")

    assert client.get(f"{API}/requests/{req['id']}", headers=triage).status_code == 200
    assert req["id"] in [r["id"] for r in client.get(f"{API}/requests?view=triage", headers=triage).json()["items"]]
    assert client.get(f"{API}/requests/{req['id']}", headers=other).status_code == 404
    assert client.get(f"{API}/requests?view=triage", headers=other).status_code == 403
    assert req["id"] not in [r["id"] for r in client.get(f"{API}/requests", headers=other).json()["items"]]
    assert client.post(f"{API}/requests/{req['id']}/override", headers=other,
                       json={"priority": "High", "reason": "not my queue"}).status_code == 404
    with pytest.raises(WebSocketDisconnect) as closed:
        with client.websocket_connect(f"/ws/requests/{req['id']}?token={other['Authorization'].split()[1]}"):
            pass
    assert closed.value.code == 4403


def test_staff_without_unit_cannot_see_unassigned_requests(client, db):
    req, _ = submit(client, "help please!!")
    user = db.query(User).filter_by(email="agent1.it@qoldau.edu.kz").one()
    user.unit_id = None
    db.commit()
    headers = login(client, user.email)
    assert client.get(f"{API}/requests/{req['id']}", headers=headers).status_code == 404
    assert req["id"] not in [r["id"] for r in client.get(f"{API}/requests", headers=headers).json()["items"]]


def test_cross_unit_request_and_attachment_access_are_revoked(client, db):
    req, student = submit(client, "the library catalog shows the book available but it is not on the shelf")
    assert req["unit"]["name"] == "Main Library Desk"
    library = login(client, "agent1.library@qoldau.edu.kz")
    other = login(client, "agent1.it@qoldau.edu.kz")
    assert client.get(f"{API}/requests/{req['id']}", headers=other).status_code == 404
    assert client.post(f"{API}/requests/{req['id']}/messages", headers=other,
                       json={"body": "Should be denied"}).status_code == 404

    upload = client.post(f"{API}/requests/{req['id']}/attachments", headers=library,
                         files={"file": ("proof.png", b"\x89PNG\r\n\x1a\nexample", "image/png")})
    assert upload.status_code == 201, upload.text
    url = upload.json()["url"]
    assert client.get(url).status_code == 200

    db_req = db.get(Request, req["id"])
    db_req.unit_id = db.query(Unit).filter_by(name="IT Help Desk").one().id
    db_req.assignee_id = None
    db.commit()
    assert client.get(url).status_code == 404
    assert client.get(f"{API}/requests/{req['id']}", headers=library).status_code == 404
    assert client.get(f"{API}/requests/{req['id']}", headers=other).status_code == 200

    student_user = db.query(User).filter_by(email="student@qoldau.edu.kz").one()
    assert student_user.role == Role.STUDENT
    student_user.is_active = False
    db.commit()
    assert client.get(f"{API}/requests/{req['id']}", headers=student).status_code == 401
