"""Retraining from agent feedback and model version management (US18).

Pipeline: dataset builder (seed data + ai_feedback corrections, de-duplicated, latest correction
wins) -> stratified train / hold-out split -> TF-IDF + Logistic Regression (the Sprint 2 algorithm)
-> evaluation (accuracy, macro-F1, per-class F1, confusion matrix) -> versioned artifact
(artifacts/classifier/v1.3/model.joblib) -> model_registry row.

Promotion: a new version is activated automatically only if its macro-F1 >= the active version's;
otherwise it stays a Candidate. Admins can activate any version or roll back. Activation swaps the
in-memory model at once in this process; other workers pick it up from model_registry within
model_sync_seconds (sync_active_model runs on the scheduler), so there is no downtime.

Usage:  python -m app.ml.training [--force]
"""
from __future__ import annotations

import argparse
import logging
import re
import traceback
from collections import Counter
from pathlib import Path

import joblib
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import SessionLocal, utcnow
from ..models import AIFeedback, AuditLog, ModelRegistry, Request, TrainingRun, User
from . import classifier, dataset

log = logging.getLogger(__name__)

CLASSIFIER = "classifier"
PRIORITY = "priority"
MIN_PRIORITY_SAMPLES = 50
_VERSION = re.compile(r"^v(\d+)\.(\d+)$")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


# ---------------- datasets ----------------
def classifier_dataset(db: Session) -> tuple[list[str], list[str], int]:
    """Seed data + agent corrections; for the same text the latest correction wins."""
    data: dict[str, tuple[str, str]] = {_norm(t): (t, c) for t, c in dataset.generate()}
    n_fb = 0
    for fb in (db.query(AIFeedback).filter(AIFeedback.corrected_category.isnot(None)).order_by(AIFeedback.id)):
        data[_norm(fb.text)] = (fb.text, fb.corrected_category)
        n_fb += 1
    texts, labels = zip(*data.values()) if data else ((), ())
    return list(texts), list(labels), n_fb


def priority_dataset(db: Session) -> tuple[list[str], list[str], int]:
    """Final priorities of past requests + agent priority corrections (latest wins)."""
    data: dict[str, tuple[str, str]] = {}
    for subject, description, prio in db.query(Request.subject, Request.description, Request.priority):
        text = f"{subject}\n{description}"
        data[_norm(text)] = (text, prio)
    n_fb = 0
    for fb in (db.query(AIFeedback).filter(AIFeedback.corrected_priority.isnot(None)).order_by(AIFeedback.id)):
        data[_norm(fb.text)] = (fb.text, fb.corrected_priority)
        n_fb += 1
    texts, labels = zip(*data.values()) if data else ((), ())
    return list(texts), list(labels), n_fb


def feedback_since_last_training(db: Session) -> int:
    last = db.query(func.max(ModelRegistry.trained_at)).filter(ModelRegistry.model_type == CLASSIFIER).scalar()
    q = db.query(AIFeedback).filter(AIFeedback.corrected_category.isnot(None) | AIFeedback.corrected_priority.isnot(None))
    if last:
        q = q.filter(AIFeedback.created_at > last)
    return q.count()


# ---------------- train & evaluate ----------------
def train_and_evaluate(texts: list[str], labels: list[str], seed: int = 42):
    counts = Counter(labels)
    stratify = labels if min(counts.values()) >= 2 else None
    x_tr, x_te, y_tr, y_te = train_test_split(texts, labels, test_size=0.2, stratify=stratify, random_state=seed)
    model = classifier._build_pipeline().fit(x_tr, y_tr)
    pred = model.predict(x_te)
    names = sorted(counts)
    per_class = f1_score(y_te, pred, labels=names, average=None, zero_division=0)
    metrics = {
        "accuracy": round(float(accuracy_score(y_te, pred)), 4),
        "macro_f1": round(float(f1_score(y_te, pred, average="macro", zero_division=0)), 4),
        "per_class_f1": {n: round(float(f), 4) for n, f in zip(names, per_class)},
        "confusion_matrix": {"labels": names, "matrix": confusion_matrix(y_te, pred, labels=names).tolist()},
        "train_size": len(x_tr),
        "test_size": len(x_te),
    }
    final = classifier._build_pipeline().fit(texts, labels)  # the shipped model sees all data
    return final, metrics


def next_version(db: Session, model_type: str) -> str:
    minors = [int(m.group(2)) for (v,) in db.query(ModelRegistry.version).filter_by(model_type=model_type)
              if (m := _VERSION.match(v))]
    return f"v1.{max(minors) + 1 if minors else 1}"


def artifact_dir() -> Path:
    return get_settings().model_dir


def _audit(db: Session, actor: User | None, reg: ModelRegistry, action: str, detail: dict) -> None:
    db.add(AuditLog(actor_id=actor.id if actor else None, entity="model", entity_id=str(reg.id), action=action,
                    old=None, new={"model_type": reg.model_type, "version": reg.version, **detail}))


def activate(db: Session, reg: ModelRegistry, actor: User | None, action: str = "activate") -> None:
    """Make reg the active version of its type. The caller commits; the swap happens after commit."""
    previous = (db.query(ModelRegistry).filter(ModelRegistry.model_type == reg.model_type,
                                               ModelRegistry.is_active.is_(True), ModelRegistry.id != reg.id).all())
    for p in previous:
        p.is_active, p.status = False, "archived"
    reg.is_active, reg.status = True, "active"
    reg.activated_by, reg.activated_at = (actor.id if actor else None), utcnow()
    _audit(db, actor, reg, action, {"previous": [p.version for p in previous], "macro_f1": reg.macro_f1})
    from ..services import jobs
    jobs.after_commit(db, sync_active_model_job)


def _train_one(db: Session, run: TrainingRun, model_type: str, say) -> dict | None:
    texts, labels, n_fb = (classifier_dataset if model_type == CLASSIFIER else priority_dataset)(db)
    if model_type == PRIORITY and (len(texts) < MIN_PRIORITY_SAMPLES or len(set(labels)) < 2):
        say(f"[{model_type}] skipped: only {len(texts)} labelled samples (need {MIN_PRIORITY_SAMPLES}+)")
        return None
    say(f"[{model_type}] dataset: {len(texts)} samples, {len(set(labels))} classes, {n_fb} agent corrections")
    pipeline, metrics = train_and_evaluate(texts, labels)
    version = next_version(db, model_type)
    rel = Path(model_type) / version / "model.joblib"
    path = artifact_dir() / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipeline, "version": version, "metrics": metrics}, path)
    say(f"[{model_type}] {version}: accuracy {metrics['accuracy']:.3f}, macro-F1 {metrics['macro_f1']:.3f} "
        f"(hold-out n={metrics['test_size']})")
    reg = ModelRegistry(version=version, model_type=model_type, algorithm=classifier.ALGORITHM,
                        accuracy=metrics["accuracy"], macro_f1=metrics["macro_f1"], metrics=metrics,
                        train_size=metrics["train_size"], feedback_count=n_fb, status="candidate", is_active=False,
                        artifact_path=rel.as_posix(), training_run_id=run.id)
    db.add(reg)
    db.flush()
    active = db.query(ModelRegistry).filter_by(model_type=model_type, is_active=True).first()
    promoted = active is None or reg.macro_f1 >= active.macro_f1
    if promoted:
        activate(db, reg, None, action="promote")
        say(f"[{model_type}] {version} activated (macro-F1 {reg.macro_f1:.3f} >= "
            f"{active.macro_f1:.3f} of {active.version})" if active else f"[{model_type}] {version} activated")
    else:
        say(f"[{model_type}] {version} kept as candidate: macro-F1 {reg.macro_f1:.3f} < "
            f"{active.macro_f1:.3f} of active {active.version}")
    return {"version": version, "macro_f1": reg.macro_f1, "accuracy": reg.accuracy, "promoted": promoted,
            "registry_id": reg.id}


def run_training(run_id: int) -> None:
    """Background job: train, evaluate and register new classifier + priority versions."""
    db = SessionLocal()
    run = db.get(TrainingRun, run_id)
    if run is None:
        db.close()
        return
    lines: list[str] = []

    def say(msg: str) -> None:
        lines.append(f"{utcnow():%H:%M:%S} {msg}")
        run.logs = "\n".join(lines)
        log.info("training run %s: %s", run_id, msg)

    try:
        run.status, run.started_at = "running", utcnow()
        say(f"started ({run.trigger}{', forced' if run.force else ''})")
        db.commit()
        result = {}
        for model_type in (CLASSIFIER, PRIORITY):
            result[model_type] = _train_one(db, run, model_type, say)
            db.commit()
        run.result, run.status, run.finished_at = result, "done", utcnow()
        say("finished")
        db.commit()
    except Exception as exc:
        db.rollback()
        run = db.get(TrainingRun, run_id)
        run.status, run.finished_at, run.error = "failed", utcnow(), f"{type(exc).__name__}: {exc}"
        run.logs = "\n".join(lines + [traceback.format_exc(limit=3)])
        db.commit()
        log.exception("training run %s failed", run_id)
    finally:
        db.close()


def start_run(db: Session, actor: User | None, force: bool, trigger: str = "manual") -> TrainingRun:
    run = TrainingRun(status="queued", trigger=trigger, force=force, requested_by=actor.id if actor else None,
                      feedback_count=feedback_since_last_training(db))
    db.add(run)
    db.flush()
    from ..services import jobs
    jobs.after_commit(db, run_training, run.id)
    return run


def running(db: Session) -> TrainingRun | None:
    return db.query(TrainingRun).filter(TrainingRun.status.in_(("queued", "running"))).first()


def scheduled_retrain() -> None:
    """Weekly job: retrain when enough new feedback has arrived."""
    db = SessionLocal()
    try:
        if running(db) is None and feedback_since_last_training(db) >= get_settings().retrain_min_feedback:
            start_run(db, None, force=False, trigger="schedule")
            db.commit()
    finally:
        db.close()


# ---------------- hot swap ----------------
def sync_active_model(db: Session) -> str | None:
    """Load the active classifier from model_registry if this process runs a different version."""
    active = db.query(ModelRegistry).filter_by(model_type=CLASSIFIER, is_active=True).first()
    current = classifier.current_version()
    if active is None or active.version == current:
        if active is None and current is not None and current != _default_version():
            classifier.reset()  # e.g. registry emptied: back to the default artifact
        return current
    path = artifact_dir() / (active.artifact_path or classifier.model_path().name)
    if not path.exists():
        log.error("active model %s has no artifact at %s; keeping %s", active.version, path, current)
        return current
    clf, metrics = classifier.load_artifact(path)
    classifier.swap(clf, metrics)
    log.info("classifier hot-swapped %s -> %s", current, clf.version)
    return clf.version


_default_cache: tuple[float, str | None] | None = None


def _default_version() -> str | None:
    global _default_cache
    path = classifier.model_path()
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    if _default_cache is None or _default_cache[0] != mtime:
        try:
            _default_cache = (mtime, joblib.load(path)["version"])
        except Exception:
            _default_cache = (mtime, None)
    return _default_cache[1]


def sync_active_model_job() -> None:
    db = SessionLocal()
    try:
        sync_active_model(db)
    except Exception:
        log.exception("model sync failed")
    finally:
        db.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="retrain even with fewer than 200 new corrections")
    args = ap.parse_args()
    db = SessionLocal()
    try:
        n = feedback_since_last_training(db)
        if n < get_settings().retrain_min_feedback and not args.force:
            print(f"Only {n} new feedback items (need {get_settings().retrain_min_feedback}); use --force.")
            return
        run = TrainingRun(status="queued", trigger="manual", force=args.force, feedback_count=n)
        db.add(run)
        db.commit()
        run_training(run.id)
        db.refresh(run)
        print(run.logs)
    finally:
        db.close()


if __name__ == "__main__":
    main()
