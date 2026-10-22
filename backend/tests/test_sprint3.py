"""US11 (timeline & search), US12 (SLA), US13 (analytics), US14 (admin), US15 (messaging & CSAT)."""
from datetime import timedelta

from app.db import utcnow
from app.models import AuditLog, Category, Escalation, Notification, Request, Status, Unit, User
from app.services import sla
from conftest import login, set_online


def _submit(client, text, email="student@qoldau.edu.kz", subject="Request"):
    h = login(client, email)
    r = client.post("/api/v1/requests", headers=h, json={"subject": subject, "description": text})
    assert r.status_code == 201, r.text
    return r.json(), h


# ---------- US11 ----------
def test_timeline_is_ordered_and_public(client, db):
    req, hs = _submit(client, "the window in my room does not close")
    tl = client.get(f"/api/v1/requests/{req['id']}/timeline", headers=hs).json()
    kinds = [e["kind"] for e in tl]
    assert kinds[0] == "submitted"
    assert [e["title"] for e in tl][:2] == ["Submitted", "Classified"]
    classified = next(e for e in tl if e["title"] == "Classified")
    assert "%" in classified["detail"]  # category + confidence
    assert any(e["kind"] == "routing" and "Student Housing Office" in e["title"] for e in tl)
    stamps = [e["created_at"] for e in tl]
    assert stamps == sorted(stamps)


def test_search_by_id_keyword_filter_and_pagination(client, db):
    h = login(client, "student@qoldau.edu.kz")
    ids = []
    for i in range(22):
        text = "the heating in my dormitory room is not working" if i % 2 else "my university email account is locked"
        ids.append(client.post("/api/v1/requests", headers=h, json={"subject": f"Req {i}", "description": text}).json()["id"])
    page1 = client.get("/api/v1/requests", headers=h).json()
    assert page1["total"] == 22 and len(page1["items"]) == 20 and page1["pages"] == 2
    one = client.get(f"/api/v1/requests?q={ids[5]}", headers=h).json()
    assert [i["id"] for i in one["items"]] == [ids[5]]
    dorm = client.get("/api/v1/requests?q=dormitory&status=Routed", headers=h).json()
    assert dorm["total"] == 11 and all(i["status"] == "Routed" for i in dorm["items"])
    assert client.get("/api/v1/requests", headers=h).json()["total"] == 22


# ---------- US12 ----------
def _critical_finance(client, db):
    set_online(db, "agent1.finance@qoldau.edu.kz")
    req, hs = _submit(client, "Urgent: someone is harassing me about my scholarship payment, I feel unsafe")
    r = db.get(Request, req["id"])
    fin = db.query(Unit).filter_by(name="Finance Office").one()
    r.unit_id, r.priority = fin.id, "Critical"
    sla.assign_due_dates(db, r, start=r.created_at)
    db.commit()
    return r, hs


def test_sla_warning_at_80_percent_and_breach_escalation(client, db):
    r, _ = _critical_finance(client, db)
    assert r.sla_first_response_due - r.created_at == timedelta(hours=1)
    sla.run_tick(db, now=r.created_at + timedelta(minutes=45))
    assert db.query(Escalation).filter_by(request_id=r.id, kind="sla_warning").count() == 0
    sla.run_tick(db, now=r.created_at + timedelta(minutes=49))
    assert db.query(Escalation).filter_by(request_id=r.id, kind="sla_warning").count() == 1
    state = sla.state(sla.policy_hours(db)["Critical"], r, now=r.created_at + timedelta(minutes=49))
    assert state["color"] == "red"
    sla.run_tick(db, now=r.created_at + timedelta(minutes=61))
    db.refresh(r)
    assert r.sla_breached and r.escalated
    head = db.get(User, db.get(Unit, r.unit_id).head_user_id)
    assert db.query(Notification).filter_by(user_id=head.id, type="sla_breach", request_id=r.id).count() == 1
    assert db.query(Escalation).filter_by(request_id=r.id, kind="sla_breach").count() == 1
    # Idempotent: a second tick does not escalate again.
    sla.run_tick(db, now=r.created_at + timedelta(minutes=62))
    assert db.query(Escalation).filter_by(request_id=r.id, kind="sla_breach").count() == 1


def test_breach_raises_priority_one_level(client, db):
    req, _ = _submit(client, "the library catalog shows the book available but it is not on the shelf")
    r = db.get(Request, req["id"])
    before = r.priority
    sla.run_tick(db, now=r.sla_first_response_due + timedelta(minutes=1))
    db.refresh(r)
    assert r.priority == {"Low": "Medium", "Medium": "High", "High": "Critical", "Critical": "Critical"}[before]


def test_sla_paused_while_waiting_for_student(client, db):
    req, hs = _submit(client, "the shower in the dorm is broken for a week")
    h = login(client, "agent1.housing@qoldau.edu.kz")
    client.patch(f"/api/v1/requests/{req['id']}/status", headers=h, json={"status": "In Progress"})
    client.patch(f"/api/v1/requests/{req['id']}/status", headers=h,
                 json={"status": "Waiting for Student", "message": "When can we visit?"})
    r = db.get(Request, req["id"])
    db.refresh(r)
    due_before = r.sla_resolution_due
    assert r.sla_paused_at is not None
    summary = sla.run_tick(db, now=utcnow() + timedelta(days=2))
    db.refresh(r)
    assert summary["breaches"] == 0 and not r.sla_breached
    # Student replies -> timer resumes and due date moves forward by the paused time.
    r.sla_paused_at = utcnow() - timedelta(days=2)
    db.commit()
    assert client.post(f"/api/v1/requests/{req['id']}/messages", headers=hs, json={"body": "Tomorrow at 10"}).status_code == 201
    db.refresh(r)
    assert r.status == Status.IN_PROGRESS and r.sla_paused_at is None
    assert r.sla_resolution_due - due_before >= timedelta(days=2) - timedelta(minutes=1)


def test_working_hours_calendar():
    from datetime import datetime
    # Friday 17:00 local (12:00 UTC) + 4 working hours -> Monday 12:00 local (07:00 UTC)
    start = datetime(2026, 10, 16, 12, 0)
    due = sla.add_hours(start, 4, "Mon-Fri 09:00-18:00", True)
    assert due == datetime(2026, 10, 19, 7, 0)


# ---------- US13 ----------
def test_analytics_filters_and_unit_head_lock(client, db):
    _submit(client, "the campus Wi-Fi does not connect on my laptop")
    _submit(client, "I want to extend the return date of a library book")
    ha = login(client, "admin@qoldau.edu.kz")
    it = db.query(Unit).filter_by(name="IT Help Desk").one()
    data = client.get(f"/api/v1/analytics/dashboard?days=30&unit_id={it.id}", headers=ha).json()
    assert data["kpis"]["total"] == db.query(Request).filter_by(unit_id=it.id).count()
    hl = login(client, "head.library@qoldau.edu.kz")
    lib = db.query(Unit).filter_by(name="Main Library Desk").one()
    data = client.get(f"/api/v1/analytics/dashboard?unit_id={it.id}", headers=hl).json()
    assert data["filters"]["unit_id"] == lib.id
    assert data["kpis"]["total"] == db.query(Request).filter_by(unit_id=lib.id).count()
    assert all(u["unit"] == "Main Library Desk" for u in data["by_unit"])


def test_sla_compliance_never_exceeds_100(client, db):
    for _ in range(3):
        req, _ = _submit(client, "the campus Wi-Fi does not connect on my laptop")
        r = db.get(Request, req["id"])
        r.status, r.resolved_at = Status.RESOLVED, r.created_at + timedelta(hours=1)
    db.commit()
    k = client.get("/api/v1/analytics/summary", headers=login(client, "admin@qoldau.edu.kz")).json()
    assert 0 <= k["sla_compliance"] <= 100


# ---------- US14 ----------
def test_admin_routing_rule_takes_effect_and_is_audited(client, db):
    ha = login(client, "admin@qoldau.edu.kz")
    lib_cat = db.query(Category).filter_by(name="Library").one()
    deans = db.query(Unit).filter_by(name="Dean's Office").one()
    lib_unit = db.query(Unit).filter_by(name="Main Library Desk").one()
    client.post("/api/v1/admin/routing-rules", headers=ha, json={"category_id": lib_cat.id, "unit_id": deans.id})
    req, _ = _submit(client, "I want to extend the return date of a library book")
    assert req["unit"]["name"] == "Dean's Office"
    r = client.post("/api/v1/admin/routing-rules", headers=ha, json={"category_id": lib_cat.id, "unit_id": lib_unit.id})
    assert r.status_code == 201
    rules = client.get("/api/v1/admin/routing-rules", headers=ha).json()
    assert any(x["category_name"] == "Library" and x["unit_name"] == "Main Library Desk" and x["is_active"] for x in rules)
    assert db.query(AuditLog).filter_by(entity="routing_rule", action="create").count() == 2
    req, _ = _submit(client, "I want to extend the return date of a library book")
    assert req["unit"]["name"] == "Main Library Desk"


def test_non_admin_gets_403(client, db):
    h = login(client, "agent1.it@qoldau.edu.kz")
    lib_cat = db.query(Category).filter_by(name="Library").one()
    assert client.get("/api/v1/admin/routing-rules", headers=h).status_code == 403
    assert client.post("/api/v1/admin/routing-rules", headers=h,
                       json={"category_id": lib_cat.id, "unit_id": 1}).status_code == 403
    assert db.query(AuditLog).count() == 0


def test_cannot_delete_unit_with_open_requests(client, db):
    req, _ = _submit(client, "the campus Wi-Fi does not connect on my laptop")
    ha = login(client, "admin@qoldau.edu.kz")
    it = db.query(Unit).filter_by(name="IT Help Desk").one()
    r = client.delete(f"/api/v1/admin/units/{it.id}", headers=ha)
    assert r.status_code == 409


def test_admin_keyword_changes_scoring_without_redeploy(client, db):
    ha = login(client, "admin@qoldau.edu.kz")
    assert client.post("/api/v1/admin/keywords", headers=ha,
                       json={"keyword": "flood", "weight": 50, "is_critical": True}).status_code == 201
    req, _ = _submit(client, "there is a flood in the dormitory bathroom")
    assert req["priority"] == "Critical"


# ---------- US15 ----------
PDF = b"%PDF-1.4\n" + b"0" * (2 * 1024 * 1024)


def test_message_with_pdf_and_read_receipt(client, db):
    set_online(db, "agent1.finance@qoldau.edu.kz")
    req, hs = _submit(client, "I was charged twice for the semester fee")
    up = client.post(f"/api/v1/requests/{req['id']}/attachments", headers=hs,
                     files={"file": ("receipt.pdf", PDF, "application/pdf")})
    assert up.status_code == 201, up.text
    msg = client.post(f"/api/v1/requests/{req['id']}/messages", headers=hs,
                      json={"body": "Here is the receipt", "attachment_ids": [up.json()["id"]]}).json()
    agent_email = db.get(User, db.get(Request, req["id"]).assignee_id).email
    ha = login(client, agent_email)
    msgs = client.get(f"/api/v1/requests/{req['id']}/messages", headers=ha).json()
    att = msgs[-1]["attachments"][0]
    assert att["filename"] == "receipt.pdf"
    assert client.get(att["url"]).status_code == 200
    mine = client.get(f"/api/v1/requests/{req['id']}/messages", headers=hs).json()
    assert next(m for m in mine if m["id"] == msg["id"])["read_at"] is not None
    # Tampered signature is rejected.
    assert client.get(att["url"].replace("sig=", "sig=0")).status_code == 403


def test_reject_exe_and_oversized_files(client, db):
    req, hs = _submit(client, "I was charged twice for the semester fee")
    exe = client.post(f"/api/v1/requests/{req['id']}/attachments", headers=hs,
                      files={"file": ("setup.exe", b"MZ" + b"0" * 100, "application/octet-stream")})
    assert exe.status_code == 415
    big = client.post(f"/api/v1/requests/{req['id']}/attachments", headers=hs,
                      files={"file": ("big.pdf", b"%PDF" + b"0" * (11 * 1024 * 1024), "application/pdf")})
    assert big.status_code == 413
    fake = client.post(f"/api/v1/requests/{req['id']}/attachments", headers=hs,
                       files={"file": ("virus.pdf", b"MZ-not-a-pdf", "application/pdf")})
    assert fake.status_code == 415


def test_low_csat_reopens_and_feeds_analytics(client, db):
    set_online(db, "agent1.it@qoldau.edu.kz")
    req, hs = _submit(client, "my university email account is locked")
    agent_email = db.get(User, db.get(Request, req["id"]).assignee_id).email
    ha = login(client, agent_email)
    client.patch(f"/api/v1/requests/{req['id']}/status", headers=ha, json={"status": "In Progress"})
    client.patch(f"/api/v1/requests/{req['id']}/status", headers=ha, json={"status": "Resolved", "message": "Unlocked"})
    r = client.post(f"/api/v1/requests/{req['id']}/csat", headers=hs, json={"rating": 2, "comment": "not solved"})
    assert r.status_code == 201
    detail = client.get(f"/api/v1/requests/{req['id']}", headers=hs).json()
    assert detail["status"] == "Reopened" and detail["csat"]["rating"] == 2
    head = db.query(User).filter_by(email="head.it@qoldau.edu.kz").one()
    assert db.query(Notification).filter_by(user_id=head.id, type="low_csat").count() == 1
    k = client.get("/api/v1/analytics/summary", headers=login(client, "admin@qoldau.edu.kz")).json()
    assert k["csat_avg"] == 2 and k["csat_count"] == 1
    assert client.post(f"/api/v1/requests/{req['id']}/csat", headers=hs, json={"rating": 5}).status_code == 409
