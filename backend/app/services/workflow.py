"""Request workflow state machine (US8).

Submitted -> Classified -> Routed -> In Progress -> Waiting for Student -> Resolved -> Closed,
plus Needs Review (triage) and Reopened. Anything else is rejected with HTTP 409.
"""
from sqlalchemy.orm import Session

from ..db import utcnow
from ..models import Request, Role, Status, StatusHistory, User
from . import jobs, notifications, sla


class TransitionNotAllowed(Exception):
    def __init__(self, from_status: str, to_status: str):
        super().__init__(f"Transition not allowed: {from_status} -> {to_status}")
        self.from_status, self.to_status = from_status, to_status


ALLOWED: dict[str, set[str]] = {
    Status.SUBMITTED: {Status.CLASSIFIED, Status.NEEDS_REVIEW},
    Status.CLASSIFIED: {Status.ROUTED, Status.NEEDS_REVIEW},
    Status.NEEDS_REVIEW: {Status.CLASSIFIED},
    Status.ROUTED: {Status.IN_PROGRESS, Status.WAITING, Status.RESOLVED, Status.NEEDS_REVIEW},
    Status.IN_PROGRESS: {Status.WAITING, Status.RESOLVED, Status.ROUTED},
    Status.WAITING: {Status.IN_PROGRESS, Status.RESOLVED},
    Status.RESOLVED: {Status.CLOSED, Status.REOPENED},
    Status.REOPENED: {Status.IN_PROGRESS, Status.WAITING, Status.RESOLVED},
    Status.CLOSED: set(),
}

# Per-category workflow templates: optional named sub-steps shown on the student timeline.
TEMPLATES: dict[str, list[str]] = {
    "standard": [],
    "approval": ["Under review", "Awaiting approval", "Decision made"],
    "document": ["Request", "Prepare", "Ready for Pickup"],
    "urgent": [],
    "triage": [],
}

STUDENT_MESSAGES = {
    Status.CLASSIFIED: "Your request has been analysed and categorised.",
    Status.NEEDS_REVIEW: "Your request is being reviewed by Student Services to find the right office.",
    Status.ROUTED: "Your request has been sent to the responsible office.",
    Status.IN_PROGRESS: "An agent is now working on your request.",
    Status.WAITING: "The agent needs more information from you. Please reply in the request chat.",
    Status.RESOLVED: "Your request has been resolved. Please rate the service.",
    Status.CLOSED: "Your request has been closed.",
    Status.REOPENED: "Your request has been reopened for review.",
}


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in ALLOWED.get(from_status, set())


def record(db: Session, req: Request, from_status: str | None, to_status: str, actor: User | None,
           reason: str, note: str | None = None) -> StatusHistory:
    h = StatusHistory(request_id=req.id, from_status=from_status, to_status=to_status,
                      actor_id=actor.id if actor else None, reason=reason, note=note)
    db.add(h)
    return h


def transition(db: Session, req: Request, to_status: str, actor: User | None, reason: str = "manual",
               note: str | None = None, notify_student: bool = True, student_message: str | None = None) -> Request:
    if to_status not in Status.ALL or not can_transition(req.status, to_status):
        raise TransitionNotAllowed(req.status, to_status)
    from_status = req.status
    now = utcnow()

    if to_status == Status.WAITING:
        sla.pause(req, now)
    elif from_status == Status.WAITING:
        sla.resume(req, now)
    if to_status == Status.RESOLVED:
        req.resolved_at = now
        from ..ml import embeddings
        if embeddings.AUTO_INDEX:  # resolved cases feed similar-request search and smart replies
            jobs.after_commit(db, embeddings.job_index_request, req.id)
    if to_status == Status.CLOSED:
        req.closed_at = now
    if to_status == Status.REOPENED:
        req.resolved_at = None
    if (actor and actor.role in Role.STAFF and req.first_response_at is None
            and to_status in (Status.WAITING, Status.RESOLVED)):
        req.first_response_at = now

    req.status = to_status
    req.updated_at = now
    record(db, req, from_status, to_status, actor, reason, note)
    db.flush()

    payload = {"event": "status_changed", "request_id": req.id, "from": from_status, "to": to_status,
               "at": now.isoformat() + "Z"}
    notifications.queue_push(db, f"request:{req.id}", payload)
    notifications.queue_push(db, f"user:{req.student_id}", payload)
    if req.unit_id:
        notifications.queue_push(db, f"unit:{req.unit_id}", {"event": "request_updated", "request_id": req.id})
    notifications.queue_push(db, "staff", {"event": "request_updated", "request_id": req.id})

    if notify_student and (actor is None or actor.id != req.student_id):
        body = student_message or STUDENT_MESSAGES.get(to_status, "")
        notifications.notify(db, req.student, "status_changed", f"{req.id}: {to_status}", body, req)
    return req


def advance_step(db: Session, req: Request, actor: User) -> Request:
    steps = TEMPLATES.get(req.workflow, [])
    if not steps or req.workflow_step >= len(steps) - 1:
        raise TransitionNotAllowed(f"step {req.workflow_step}", f"step {req.workflow_step + 1}")
    req.workflow_step += 1
    req.updated_at = utcnow()
    label = steps[req.workflow_step]
    record(db, req, req.status, req.status, actor, "manual", note=f"Workflow step: {label}")
    notifications.queue_push(db, f"request:{req.id}", {"event": "step_changed", "request_id": req.id, "step": label})
    notifications.notify(db, req.student, "step_changed", f"{req.id}: {label}", f"Your request moved to step \"{label}\".", req)
    return req
