"""Evaluate routing against an independent CSV on a disposable pilot database."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from .db import SessionLocal
from .ml import training
from .models import Escalation, Priority, Role, Status, User
from .services import pipeline


def evaluate(path: Path) -> dict:
    with path.open(encoding="utf-8-sig", newline="") as file:
        cases = list(csv.DictReader(file))
    counts = Counter(case["language"] for case in cases)
    if set(counts) != {"kz", "ru", "en"} or min(counts.values()) < 10:
        raise ValueError("Provide at least ten cases for each of kz, ru and en")
    if len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Case IDs must be unique")
    critical_languages = {case["language"] for case in cases if case["critical"] == "true"}
    if critical_languages != set(counts) or any(case["critical"] not in ("true", "false") for case in cases):
        raise ValueError("Provide a critical control case in every language and use true or false")

    correct = Counter()
    triage = Counter()
    errors = []
    critical_passed = 0
    critical_total = 0
    with SessionLocal() as db:
        training.sync_active_model(db)
        student = User(name="Pilot routing fixture", email="routing-fixture@pilot.invalid", password_hash="unused",
                       role=Role.STUDENT, is_active=False)
        db.add(student)
        db.flush()
        for case in cases:
            req = pipeline.submit(db, student, case["subject"], case["description"], student_category_id=None)
            db.flush()
            model_version = req.model_version
            routed_to_triage = req.status == Status.NEEDS_REVIEW or bool(req.unit and req.unit.is_triage)
            actual = "Triage" if routed_to_triage else req.unit.name if req.unit else "Unrouted"
            lang = case["language"]
            if routed_to_triage:
                triage[lang] += 1
            if actual == case["expected"]:
                correct[lang] += 1
            critical_ok = True
            if case["critical"] == "true":
                critical_total += 1
                alert = db.query(Escalation).filter_by(request_id=req.id, kind="critical").first()
                critical_ok = req.priority == Priority.CRITICAL and bool(alert and alert.notified_user_id)
                critical_passed += int(critical_ok)
            if actual != case["expected"] or not critical_ok:
                errors.append({"id": case["id"], "expected": case["expected"], "actual": actual,
                               "critical_ok": critical_ok, "confidence": req.ai_confidence})
        db.rollback()

    total_correct = correct.total()
    return {"model": model_version, "total": len(cases), "correct": total_correct, "triage": triage.total(),
            "by_language": {lang: {"correct": correct[lang], "total": counts[lang], "triage": triage[lang]}
                            for lang in ("kz", "ru", "en")},
            "critical_passed": critical_passed, "critical_total": critical_total, "disagreements": errors,
            "passed": total_correct * 5 >= len(cases) * 4 and critical_passed == critical_total}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(args.cases)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
