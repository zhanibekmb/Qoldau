"""US5 (classification), US6 (urgency) and US10 (model evaluation) acceptance tests."""
import time

from app.ml.classifier import get_classifier, load_or_train
from app.services import urgency
from conftest import login


def test_moodle_request_is_it_support():
    p = get_classifier().predict("Login problem", "I cannot log in to Moodle, password reset does not work")
    assert p.category == "IT Support" and p.confidence >= 0.60 and not p.needs_review


def test_transcript_for_visa_is_documents(client, db):
    h = login(client, "student@qoldau.edu.kz")
    r = client.post("/api/v1/requests", headers=h, json={
        "subject": "Transcript", "description": "I need a transcript of records for my visa application"})
    assert r.status_code == 201
    body = r.json()
    assert body["category"]["name"] == "Documents & Certificates"
    assert body["ai_confidence"] >= 0.60
    assert body["status"] == "Routed" and body["unit"]["name"] == "Registrar Office"


def test_vague_request_goes_to_triage_without_unit(client):
    h = login(client, "student@qoldau.edu.kz")
    r = client.post("/api/v1/requests", headers=h, json={"subject": "help", "description": "help please!!"})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "Needs Review"
    assert body["unit"] is None and body["assignee"] is None


def test_empty_or_one_word_does_not_crash(client):
    for text in ("", "   ", "help", "?!"):
        p = get_classifier().predict("", text)
        assert p.needs_review
    h = login(client, "student@qoldau.edu.kz")
    r = client.post("/api/v1/ai/classify", headers=h, json={"subject": "", "description": ""})
    assert r.status_code == 200 and r.json()["needs_review"] is True
    # Students never receive AI internals.
    assert r.json()["keywords"] == [] and r.json()["alternatives"] == []


def test_classification_under_one_second():
    clf = get_classifier()
    start = time.perf_counter()
    for _ in range(20):
        clf.predict("Wi-Fi", "the campus Wi-Fi does not connect on my laptop since yesterday")
    assert (time.perf_counter() - start) / 20 < 1.0


def test_model_meets_quality_targets():
    _, metrics = load_or_train()
    assert metrics["accuracy"] >= 0.85
    assert metrics["macro_f1"] >= 0.80


def test_multilingual():
    clf = get_classifier()
    assert clf.predict("", "задерживается выплата стипендии в этом месяце").category == "Finance & Scholarships"
    assert clf.predict("", "жатақхана бөлмесінде жылу жоқ, суық").category == "Dormitory & Housing"


def test_deadline_request_gets_high_or_critical(db):
    r = urgency.score(db, "Scholarship application deadline is tomorrow and the upload button fails", 38, "approval")
    assert r.priority in ("High", "Critical") and r.score >= 60


def test_exam_registration_today_high_or_critical(db):
    r = urgency.score(db, "My exam registration closes today and the system shows an error", 35, "standard")
    assert r.priority in ("High", "Critical")


def test_safety_keyword_forces_critical_and_alerts_unit(client, db):
    h = login(client, "agent1.medical@qoldau.edu.kz")  # on-duty agent is online
    hs = login(client, "student@qoldau.edu.kz")
    r = client.post("/api/v1/requests", headers=hs, json={"subject": "Help", "description": "I feel unsafe in my dorm room"})
    body = r.json()
    assert body["priority"] == "Critical" and body["priority_score"] >= 80
    notes = client.get("/api/v1/notifications", headers=h).json()
    assert any(n["type"] == "critical" and n["request_id"] == body["id"] for n in notes)


def test_low_priority_information_question(db):
    r = urgency.score(db, "I want to give feedback about the canteen food", 15, "triage")
    assert r.priority == "Low"
