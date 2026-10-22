"""US3 (Kanban), US7 (routing), US8 (workflow & notifications), US9 (override & internal notes)."""
import time

from app.models import AIFeedback, Category, EmailOutbox, Request, RoutingLog, Status, StatusHistory, Unit, User
from app.services import pipeline, routing
from conftest import login, set_offline_unit, set_online


def _submit(client, text, subject="Request", email="student@qoldau.edu.kz"):
    h = login(client, email)
    r = client.post("/api/v1/requests", headers=h, json={"subject": subject, "description": text})
    assert r.status_code == 201, r.text
    return r.json(), h


def test_finance_routed_to_least_loaded_online_agent(client, db):
    set_online(db, "agent1.finance@qoldau.edu.kz", "agent2.finance@qoldau.edu.kz", "agent3.finance@qoldau.edu.kz")
    a1 = db.query(User).filter_by(email="agent1.finance@qoldau.edu.kz").one()
    a2 = db.query(User).filter_by(email="agent2.finance@qoldau.edu.kz").one()
    # Give agents 1 and 2 some open tickets; agent 3 has none.
    for agent in (a1, a1, a2):
        req, _ = _submit(client, "my scholarship payment is delayed this month, please check")
        r = db.get(Request, req["id"])
        r.assignee_id = agent.id
        db.commit()
    start = time.perf_counter()
    req, _ = _submit(client, "I paid the tuition but the payment is not reflected in my account")
    assert time.perf_counter() - start < 2
    assert req["unit"]["name"] == "Finance Office"
    assert req["assignee"]["name"] == db.query(User).filter_by(email="agent3.finance@qoldau.edu.kz").one().name
    log = db.query(RoutingLog).filter_by(request_id=req["id"]).one()
    assert log.reason.startswith("rule: Finance & Scholarships -> Finance Office")


def test_no_agent_online_falls_back_to_unit_queue(client, db):
    set_offline_unit(db, "it")
    req, _ = _submit(client, "the campus Wi-Fi does not connect on my laptop")
    assert req["unit"]["name"] == "IT Help Desk" and req["status"] == "Routed" and req["assignee"] is None
    # First IT agent to log in sees it at the top of the New column.
    h = login(client, "agent1.it@qoldau.edu.kz")
    board = client.get("/api/v1/requests/board", headers=h).json()
    assert board["columns"]["New"][0]["id"] == req["id"]


def test_other_category_goes_to_triage_unit(client, db):
    req, _ = _submit(client, "how do I join a student club at the university, which clubs exist")
    assert req["category"]["name"] == "Other"
    assert req["unit"]["name"].startswith("Triage Queue")


def test_documents_request_lands_in_registrar_queue(client, db):
    set_online(db, "agent1.registrar@qoldau.edu.kz")
    req, _ = _submit(client, "please issue an enrollment certificate for the bank")
    assert req["unit"]["name"] == "Registrar Office" and req["assignee"] is not None
    assert req["workflow_steps"] == ["Request", "Prepare", "Ready for Pickup"]


def test_invalid_transition_rejected_and_history_unchanged(client, db):
    req, _ = _submit(client, "the shower in the dorm is broken for a week")
    h = login(client, "agent1.housing@qoldau.edu.kz")
    before = db.query(StatusHistory).filter_by(request_id=req["id"]).count()
    r = client.patch(f"/api/v1/requests/{req['id']}/status", headers=h, json={"status": "Closed"})
    assert r.status_code == 409 and r.json()["detail"]["message"] == "Transition not allowed"
    db.expire_all()
    assert db.query(StatusHistory).filter_by(request_id=req["id"]).count() == before


def test_submitted_to_closed_is_not_allowed():
    from app.services.workflow import can_transition
    assert not can_transition(Status.SUBMITTED, Status.CLOSED)
    assert can_transition(Status.ROUTED, Status.IN_PROGRESS)


def test_waiting_for_student_notifies_bell_and_email(client, db):
    req, hs = _submit(client, "the window in my room does not close")
    h = login(client, "agent1.housing@qoldau.edu.kz")
    assert client.patch(f"/api/v1/requests/{req['id']}/status", headers=h, json={"status": "In Progress"}).status_code == 200
    client.post("/api/v1/notifications/read", headers=hs)
    assert client.get("/api/v1/notifications/unread-count", headers=hs).json()["count"] == 0
    r = client.patch(f"/api/v1/requests/{req['id']}/status", headers=h,
                     json={"status": "Waiting for Student", "message": "Which room number is it?"})
    assert r.status_code == 200
    assert client.get("/api/v1/notifications/unread-count", headers=hs).json()["count"] == 1
    mail = db.query(EmailOutbox).filter(EmailOutbox.subject.contains(req["id"]),
                                        EmailOutbox.subject.contains("Waiting for Student")).one()
    assert "Which room number is it?" in mail.body and "Status: Waiting for Student" in mail.body
    # Reading resets the counter and it never goes negative.
    assert client.post("/api/v1/notifications/read", headers=hs).json()["count"] == 0
    assert client.post("/api/v1/notifications/read", headers=hs).json()["count"] == 0


def test_kanban_drag_to_in_progress_claims_card(client, db):
    set_offline_unit(db, "it")
    req, _ = _submit(client, "my university email account is locked")
    h = login(client, "agent2.it@qoldau.edu.kz")
    r = client.patch(f"/api/v1/requests/{req['id']}/status", headers=h, json={"status": "In Progress"})
    assert r.status_code == 200 and r.json()["status"] == "In Progress"
    assert r.json()["assignee"]["name"] == db.query(User).filter_by(email="agent2.it@qoldau.edu.kz").one().name
    board = client.get("/api/v1/requests/board", headers=h).json()
    assert req["id"] in [c["id"] for c in board["columns"]["In Progress"]]


def test_critical_card_on_top_of_new_column(client, db):
    set_offline_unit(db, "housing")
    _submit(client, "there are cockroaches in the dorm kitchen")
    crit, _ = _submit(client, "I feel unsafe in the dormitory, my neighbour threatens me")
    h = login(client, "agent1.housing@qoldau.edu.kz") if crit["unit"]["name"] == "Student Housing Office" else \
        login(client, "agent1.medical@qoldau.edu.kz")
    col = client.get("/api/v1/requests/board", headers=h).json()["columns"]["New"]
    assert col[0]["id"] == crit["id"] and col[0]["priority"] == "Critical"


def test_agent_override_other_to_library(client, db):
    req, hs = _submit(client, "how do I join a student club at the university, which clubs exist")
    r = db.get(Request, req["id"])
    r.ai_confidence = 0.42
    db.commit()
    lib = db.query(Category).filter_by(name="Library").one()
    h = login(client, "agent1.triage@qoldau.edu.kz")
    out = client.post(f"/api/v1/requests/{req['id']}/override", headers=h,
                      json={"category_id": lib.id, "reason": "book return question"})
    assert out.status_code == 200, out.text
    assert out.json()["unit"]["name"] == "Main Library Desk" and out.json()["category"]["name"] == "Library"
    fb = db.query(AIFeedback).filter_by(request_id=req["id"]).one()
    assert (fb.predicted_category, fb.corrected_category) == ("Other", "Library") and fb.text
    student_tl = client.get(f"/api/v1/requests/{req['id']}/timeline", headers=hs).json()
    titles = [e["title"] for e in student_tl]
    assert "Category corrected by agent" in titles
    assert not any("book return question" in (e["detail"] or "") + e["title"] for e in student_tl)


def test_override_requires_reason(client, db):
    req, _ = _submit(client, "how do I join a student club at the university, which clubs exist")
    h = login(client, "agent1.triage@qoldau.edu.kz")
    r = client.post(f"/api/v1/requests/{req['id']}/override", headers=h, json={"priority": "High", "reason": ""})
    assert r.status_code == 422


def test_needs_review_confirmed_by_agent_gets_routed(client, db):
    req, _ = _submit(client, "help please!!")
    it = db.query(Category).filter_by(name="IT Support").one()
    h = login(client, "agent1.triage@qoldau.edu.kz")
    triage = client.get("/api/v1/requests?view=triage", headers=h).json()
    assert req["id"] in [i["id"] for i in triage["items"]]
    out = client.post(f"/api/v1/requests/{req['id']}/override", headers=h,
                      json={"category_id": it.id, "reason": "student clarified by phone"}).json()
    assert out["status"] == "Routed" and out["unit"]["name"] == "IT Help Desk"


def test_internal_notes_never_visible_to_students(client, db):
    req, hs = _submit(client, "my stipend was not transferred to my bank card")
    h = login(client, "agent1.finance@qoldau.edu.kz")
    note = "student has outstanding fee - check with Finance"
    assert client.post(f"/api/v1/requests/{req['id']}/messages", headers=h,
                       json={"body": note, "is_internal": True}).status_code == 201
    client.post(f"/api/v1/requests/{req['id']}/messages", headers=h, json={"body": "We are checking."})
    student_msgs = client.get(f"/api/v1/requests/{req['id']}/messages", headers=hs).json()
    student_tl = client.get(f"/api/v1/requests/{req['id']}/timeline", headers=hs).json()
    assert all(note not in m["body"] for m in student_msgs)
    assert all(note not in (e["detail"] or "") for e in student_tl)
    staff_msgs = client.get(f"/api/v1/requests/{req['id']}/messages", headers=h).json()
    assert any(m["is_internal"] and m["body"] == note for m in staff_msgs)
    # Students cannot create internal notes, and the student detail never includes the AI panel.
    assert client.post(f"/api/v1/requests/{req['id']}/messages", headers=hs,
                       json={"body": "x", "is_internal": True}).status_code == 403
    assert client.get(f"/api/v1/requests/{req['id']}", headers=hs).json()["ai"] is None


def test_students_see_only_own_requests(client, db):
    req, _ = _submit(client, "the heating in my dormitory room is not working")
    other = login(client, "student2@qoldau.edu.kz")
    assert client.get(f"/api/v1/requests/{req['id']}", headers=other).status_code == 404
    assert all(i["id"] != req["id"] for i in client.get("/api/v1/requests", headers=other).json()["items"])
