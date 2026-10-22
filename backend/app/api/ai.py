from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..config import get_settings
from ..db import get_db
from ..ml import training
from ..ml.classifier import load_or_train
from ..models import Category, ModelRegistry, Role, TrainingRun, User
from ..security import current_user, require_admin, require_staff
from ..services import urgency

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/classify", response_model=schemas.ClassifyOut, summary="Classify free text (KZ/RU/EN) - US5")
def classify(body: schemas.ClassifyIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    clf, _ = load_or_train()
    pred = clf.predict(body.subject, body.description)
    cat = db.query(Category).filter_by(name=pred.category).first()
    staff = user.role in Role.STAFF
    return schemas.ClassifyOut(category=pred.category, category_id=cat.id if cat else None,
                               confidence=pred.confidence, needs_review=pred.needs_review,
                               alternatives=pred.alternatives if staff else [],
                               keywords=pred.keywords if staff else [], model_version=pred.model_version)


@router.post("/priority", response_model=schemas.PriorityOut, summary="Score urgency - US6")
def priority(body: schemas.ClassifyIn, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    clf, _ = load_or_train()
    pred = clf.predict(body.subject, body.description)
    cat = db.query(Category).filter_by(name=pred.category).first()
    r = urgency.score(db, f"{body.subject}\n{body.description}", cat.base_priority_weight if cat else 15,
                      cat.default_workflow if cat else "standard", pred.confidence)
    return schemas.PriorityOut(priority=r.priority, score=r.score, critical=r.critical, reasons=r.reasons)


@router.get("/model", summary="Active model version and evaluation metrics (US10)")
def model_info(db: Session = Depends(get_db), user: User = Depends(require_staff)):
    clf, metrics = load_or_train()
    reg = db.query(ModelRegistry).filter_by(version=clf.version).first()
    return {
        "version": clf.version,
        "algorithm": reg.algorithm if reg else None,
        "accuracy": reg.accuracy if reg else (metrics or {}).get("accuracy"),
        "macro_f1": reg.macro_f1 if reg else (metrics or {}).get("macro_f1"),
        "metrics": {k: v for k, v in (metrics or {}).items() if k != "per_class"},
        "per_class": (metrics or {}).get("per_class"),
    }


# ---------------- US18: retraining & model management (Admin only) ----------------
def _model_out(m: ModelRegistry, full: bool = False) -> schemas.ModelOut:
    out = schemas.ModelOut.model_validate(m)
    metrics = dict(m.metrics or {})
    if not full:
        metrics.pop("confusion_matrix", None)
        metrics.pop("per_class", None)
    out.metrics = metrics
    return out


@router.get("/models/overview", summary="Active models, feedback since last training, retrain threshold")
def models_overview(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    active = {m.model_type: _model_out(m) for m in db.query(ModelRegistry).filter_by(is_active=True)}
    run = training.running(db)
    last = db.query(TrainingRun).order_by(TrainingRun.id.desc()).first()
    return {"active": active, "feedback_since_last_training": training.feedback_since_last_training(db),
            "threshold": get_settings().retrain_min_feedback, "loaded_version": load_or_train()[0].version,
            "running_run_id": run.id if run else None,
            "last_run": schemas.TrainingRunOut.model_validate(last) if last else None}


@router.get("/models", response_model=list[schemas.ModelOut])
def list_models(model_type: str | None = Query(None, pattern="^(classifier|priority)$"),
                db: Session = Depends(get_db), _: User = Depends(require_admin)):
    q = db.query(ModelRegistry)
    if model_type:
        q = q.filter_by(model_type=model_type)
    return [_model_out(m) for m in q.order_by(ModelRegistry.trained_at.desc(), ModelRegistry.id.desc())]


@router.get("/models/{model_id}", response_model=schemas.ModelOut, summary="Version detail incl. per-class F1 and confusion matrix")
def get_model(model_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    m = db.get(ModelRegistry, model_id)
    if m is None:
        raise HTTPException(404, "Model not found")
    return _model_out(m, full=True)


@router.post("/retrain", response_model=schemas.TrainingRunOut, status_code=202,
             summary="Start a training run (needs >= 200 new agent corrections unless force=true)")
def retrain(body: schemas.RetrainIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if training.running(db):
        raise HTTPException(409, {"message": "A training run is already in progress"})
    n, need = training.feedback_since_last_training(db), get_settings().retrain_min_feedback
    if n < need and not body.force:
        raise HTTPException(409, {"message": f"Not enough new feedback: {n}/{need}. Use force to retrain anyway.",
                                  "feedback": n, "threshold": need})
    run = training.start_run(db, admin, body.force)
    db.commit()
    db.refresh(run)
    return run


@router.get("/training-runs", response_model=list[schemas.TrainingRunOut])
def training_runs(db: Session = Depends(get_db), _: User = Depends(require_admin), limit: int = Query(20, le=100)):
    return db.query(TrainingRun).order_by(TrainingRun.id.desc()).limit(limit).all()


@router.get("/training-runs/{run_id}", response_model=schemas.TrainingRunOut)
def training_run(run_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    run = db.get(TrainingRun, run_id)
    if run is None:
        raise HTTPException(404, "Training run not found")
    return run


def _switch(db: Session, model_id: int, admin: User, action: str) -> schemas.ModelOut:
    m = db.get(ModelRegistry, model_id)
    if m is None:
        raise HTTPException(404, "Model not found")
    if m.is_active:
        raise HTTPException(409, {"message": f"{m.version} is already active"})
    if m.model_type == training.CLASSIFIER and m.artifact_path and not (training.artifact_dir() / m.artifact_path).exists():
        raise HTTPException(409, {"message": f"Artifact for {m.version} is missing"})
    training.activate(db, m, admin, action=action)
    db.commit()
    return _model_out(m)


@router.post("/models/{model_id}/activate", response_model=schemas.ModelOut)
def activate_model(model_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return _switch(db, model_id, admin, "activate")


@router.post("/models/{model_id}/rollback", response_model=schemas.ModelOut,
             summary="Roll back to an earlier version (hot swap, no downtime)")
def rollback_model(model_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return _switch(db, model_id, admin, "rollback")
