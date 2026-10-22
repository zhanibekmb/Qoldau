"""End-to-end request pipeline: submit -> classify -> prioritise -> route -> SLA, plus agent override."""
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import utcnow
from ..ml.classifier import get_classifier
from ..models import AIFeedback, Category, Escalation, Priority, Request, Role, Status, Unit, User
from . import notifications, routing, sla, urgency, workflow


def next_request_id(db: Session, year: int) -> str:
    prefix = f"REQ-{year}-"
    last = db.query(func.max(Request.id)).filter(Request.id.like(prefix + "%")).scalar()
    n = int(last.rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}{n:05d}"


def _category(db: Session, name: str) -> Category | None:
    return db.query(Category).filter_by(name=name, is_active=True).first()


def classify_and_route(db: Session, req: Request, now: datetime | None = None) -> Request:
    now = now or utcnow()
    pred = get_classifier().predict(req.subject, req.description)
    cat = _category(db, pred.category) or _category(db, "Other")
    req.ai_category_id = cat.id if cat else None
    req.ai_confidence = pred.confidence
    req.ai_alternatives = pred.alternatives
    req.ai_keywords = pred.keywords
    req.model_version = pred.model_version
    req.workflow = cat.default_workflow if cat else "standard"

    weight = cat.base_priority_weight if cat else 15
    u = urgency.score(db, f"{req.subject}\n{req.description}", weight, req.workflow, pred.confidence, now=now)
    req.priority, req.priority_score, req.priority_reasons, req.ai_priority = u.priority, u.score, u.reasons, u.priority

    if pred.needs_review:
        # Low confidence: triage queue, no unit until an agent confirms the category.
        req.category_id = None
        workflow.transition(db, req, Status.NEEDS_REVIEW, actor=None, reason="AI",
                            note=f"AI confidence {pred.confidence:.0%} below threshold (best guess: {pred.category})")
        notifications.queue_push(db, "staff", {"event": "triage_new", "request_id": req.id})
    else:
        req.category_id = req.ai_category_id
        req.category = cat
        workflow.transition(db, req, Status.CLASSIFIED, actor=None, reason="AI",
                            note=f"{pred.category} ({pred.confidence:.0%})", notify_student=False)
        do_route(db, req, actor=None, kind="rule", now=now)

    if u.critical:
        alert_critical(db, req)
    return req


def do_route(db: Session, req: Request, actor: User | None, kind: str, now: datetime | None = None,
             unit: Unit | None = None, reason: str | None = None) -> None:
    entry = routing.route(db, req, actor=actor, kind=kind, unit=unit, reason_override=reason)
    sla.assign_due_dates(db, req, start=now)
    if req.status != Status.ROUTED:
        workflow.transition(db, req, Status.ROUTED, actor=actor, reason=kind, note=entry.reason)
    if req.assignee:
        notifications.notify(db, req.assignee, "assigned", f"New request assigned: {req.id}",
                             f"[{req.priority}] {req.subject}", req, email=False)
    if req.unit_id:
        notifications.queue_push(db, f"unit:{req.unit_id}", {"event": "request_new", "request_id": req.id})


def alert_critical(db: Session, req: Request) -> None:
    """Critical (health/safety) requests notify the on-duty agent(s) of the unit immediately."""
    targets: list[User] = []
    if req.assignee:
        targets = [req.assignee]
    elif req.unit_id:
        targets = [u for u in db.query(User).filter(User.unit_id == req.unit_id,
                                                    User.role.in_((Role.AGENT, Role.UNIT_HEAD)),
                                                    User.is_active.is_(True)).all()]
    else:
        targets = db.query(User).filter(User.role.in_((Role.AGENT, Role.UNIT_HEAD)), User.unit_id.is_(None)).all()
        unit = routing.triage_unit(db)
        if unit:
            targets += db.query(User).filter(User.unit_id == unit.id, User.role.in_(Role.STAFF)).all()
    for t in targets:
        notifications.notify(db, t, "critical", f"CRITICAL request {req.id}", req.subject, req)
    db.add(Escalation(request_id=req.id, kind="critical", target="-",
                      notified_user_id=targets[0].id if targets else None,
                      detail="; ".join(r for r in (req.priority_reasons or []) if "keyword" in r)))


def submit(db: Session, student: User, subject: str, description: str, student_category_id: int | None,
           now: datetime | None = None) -> Request:
    now = now or utcnow()
    req = Request(id=next_request_id(db, now.year), student_id=student.id, subject=subject.strip(),
                  description=description.strip(), student_category_id=student_category_id,
                  status=Status.SUBMITTED, created_at=now, updated_at=now)
    req.student = student
    db.add(req)
    db.flush()  # history rows reference the request id
    workflow.record(db, req, None, Status.SUBMITTED, student, "manual")
    db.flush()
    classify_and_route(db, req, now=now)
    notifications.notify(db, student, "submitted", f"Request {req.id} received",
                         f"We received your request \"{req.subject}\".", req)
    return req


def override(db: Session, req: Request, agent: User, reason: str, category_id: int | None = None,
             priority: str | None = None, unit_id: int | None = None) -> Request:
    """Agent correction of the AI decision; saved as ai_feedback and re-routes when needed."""
    new_cat = db.get(Category, category_id) if category_id else None
    new_unit = db.get(Unit, unit_id) if unit_id else None
    old_cat = req.category or req.ai_category
    old_unit = req.unit
    changed_cat = new_cat is not None and (req.category_id != new_cat.id or req.status == Status.NEEDS_REVIEW)
    changed_prio = priority is not None and priority != req.priority
    changed_unit = new_unit is not None and new_unit.id != req.unit_id

    db.add(AIFeedback(
        request_id=req.id, text=f"{req.subject}\n{req.description}",
        predicted_category=req.ai_category.name if req.ai_category else None,
        corrected_category=new_cat.name if new_cat else None,
        predicted_priority=req.ai_priority, corrected_priority=priority if changed_prio else None,
        predicted_unit=old_unit.name if old_unit else None, corrected_unit=new_unit.name if new_unit else None,
        agent_id=agent.id, reason=reason, model_version=req.model_version,
    ))

    if changed_prio:
        workflow.record(db, req, req.status, req.status, agent, "manual",
                        note=f"Priority corrected by agent: {req.priority} -> {priority} | reason: {reason}")
        req.priority = priority
        req.priority_score = {Priority.CRITICAL: 85, Priority.HIGH: 70, Priority.MEDIUM: 45, Priority.LOW: 20}[priority]
        sla.assign_due_dates(db, req, start=req.created_at)

    if changed_cat:
        req.category_id, req.category = new_cat.id, new_cat
        req.workflow = new_cat.default_workflow
        workflow.record(db, req, req.status, req.status, agent, "manual",
                        note=f"Category corrected by agent: {old_cat.name if old_cat else '-'} -> {new_cat.name} | reason: {reason}")
        if req.status == Status.NEEDS_REVIEW:
            workflow.transition(db, req, Status.CLASSIFIED, actor=agent, reason="manual",
                                note=f"{new_cat.name} (confirmed by agent)", notify_student=False)
        if not changed_unit:
            target, _ = routing.resolve_unit(db, new_cat)
            if target and target.id != req.unit_id or req.status == Status.CLASSIFIED:
                _reroute(db, req, agent, target, f"manual: category corrected -> {target.name if target else '-'}")

    if changed_unit:
        if req.status == Status.NEEDS_REVIEW:
            workflow.transition(db, req, Status.CLASSIFIED, actor=agent, reason="manual", notify_student=False)
        _reroute(db, req, agent, new_unit, f"manual: unit corrected -> {new_unit.name}")

    req.updated_at = utcnow()
    notifications.queue_push(db, f"request:{req.id}", {"event": "request_updated", "request_id": req.id})
    return req


def _reroute(db: Session, req: Request, agent: User, unit: Unit | None, reason: str) -> None:
    if req.status in (Status.IN_PROGRESS,):
        workflow.transition(db, req, Status.ROUTED, actor=agent, reason="manual", note=reason, notify_student=False)
    if req.status in (Status.ROUTED, Status.CLASSIFIED):
        entry = routing.route(db, req, actor=agent, kind="manual", unit=unit)
        entry.reason = reason + ("; assigned to " + req.assignee.name if req.assignee else "; unit queue")
        if req.status == Status.CLASSIFIED:
            sla.assign_due_dates(db, req, start=req.created_at)
            workflow.transition(db, req, Status.ROUTED, actor=agent, reason="manual", note=entry.reason)
        if req.assignee and req.assignee.id != agent.id:
            notifications.notify(db, req.assignee, "assigned", f"Request re-routed to you: {req.id}", req.subject, req,
                                 email=False)
        if req.unit_id:
            notifications.queue_push(db, f"unit:{req.unit_id}", {"event": "request_new", "request_id": req.id})
