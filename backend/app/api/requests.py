import math
from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, or_
from sqlalchemy.orm import Session, joinedload

from .. import schemas
from ..db import get_db, utcnow
from ..models import Category, Message, Request, Role, RoutingLog, Status, Unit, User
from ..security import current_user, require_roles, require_staff
from ..services import notifications, pipeline, sla, suggestions, timeline, workflow
from .common import card, detail, get_request_or_404, require_staff_access, visibility_filter

router = APIRouter(prefix="/requests", tags=["requests"])

PRIORITY_RANK = case({"Critical": 4, "High": 3, "Medium": 2, "Low": 1}, value=Request.priority)
KANBAN_COLUMNS: dict[str, tuple[str, ...]] = {
    "New": (Status.SUBMITTED, Status.CLASSIFIED, Status.ROUTED, Status.NEEDS_REVIEW, Status.REOPENED),
    "In Progress": (Status.IN_PROGRESS,),
    "Pending Student": (Status.WAITING,),
    "Closed": (Status.RESOLVED, Status.CLOSED),
}


def _transition_or_409(db: Session, req: Request, to_status: str, actor: User, **kw) -> None:
    try:
        workflow.transition(db, req, to_status, actor=actor, **kw)
    except workflow.TransitionNotAllowed as e:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, {"message": "Transition not allowed",
                                                       "from": e.from_status, "to": e.to_status})


@router.post("", response_model=schemas.RequestDetail, status_code=201)
def create_request(body: schemas.RequestCreate, db: Session = Depends(get_db),
                   user: User = Depends(require_roles(Role.STUDENT))):
    if body.category_id is not None and db.get(Category, body.category_id) is None:
        raise HTTPException(422, "Unknown category")
    req = pipeline.submit(db, user, body.subject, body.description, body.category_id)
    if body.suggestion_session:
        suggestions.attach_session(db, req, user, body.suggestion_session)
    db.commit()
    return detail(req, db, user)


@router.get("", response_model=schemas.Page)
def list_requests(
    db: Session = Depends(get_db), user: User = Depends(current_user),
    q: str | None = Query(None, max_length=200, description="Request ID or keyword"),
    status_: list[str] | None = Query(None, alias="status"),
    category_id: int | None = None, priority: str | None = None, unit_id: int | None = None,
    assignee: str | None = Query(None, description="'me', 'unassigned' or a user id"),
    date_from: date | None = None, date_to: date | None = None,
    view: Literal["all", "triage", "escalated"] = "all",
    sort: Literal["newest", "oldest", "priority", "sla"] = "newest",
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
):
    query = visibility_filter(db.query(Request), user, db)
    if q:
        term = q.strip()
        like = f"%{term}%"
        query = query.filter(or_(Request.id.ilike(like), Request.subject.ilike(like), Request.description.ilike(like)))
    if status_:
        query = query.filter(Request.status.in_(status_))
    if category_id:
        query = query.filter(Request.category_id == category_id)
    if priority:
        query = query.filter(Request.priority == priority)
    if unit_id:
        query = query.filter(Request.unit_id == unit_id)
    if assignee == "me":
        query = query.filter(Request.assignee_id == user.id)
    elif assignee == "unassigned":
        query = query.filter(Request.assignee_id.is_(None))
    elif assignee and assignee.isdigit():
        query = query.filter(Request.assignee_id == int(assignee))
    if date_from:
        query = query.filter(Request.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Request.created_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time()))
    if view == "triage":
        if user.role == Role.STUDENT:
            raise HTTPException(403, "Access denied")
        query = query.filter(Request.status == Status.NEEDS_REVIEW)
    elif view == "escalated":
        query = query.filter(Request.escalated.is_(True), Request.status.in_(Status.OPEN))

    order = {
        "newest": [Request.created_at.desc()],
        "oldest": [Request.created_at.asc()],
        "priority": [Request.priority_score.desc(), Request.created_at.asc()],
        "sla": [Request.sla_resolution_due.asc()],
    }[sort]
    total = query.count()
    rows = (query.options(joinedload(Request.category), joinedload(Request.unit), joinedload(Request.assignee),
                          joinedload(Request.student))
            .order_by(*order).offset((page - 1) * page_size).limit(page_size).all())
    hours = sla.policy_hours(db)
    return schemas.Page(items=[card(r, hours, user) for r in rows], total=total, page=page, page_size=page_size,
                        pages=max(1, math.ceil(total / page_size)))


@router.get("/board", summary="Kanban board for the agent's unit (US3)")
def board(db: Session = Depends(get_db), user: User = Depends(require_staff),
          unit_id: int | None = None, mine: bool = False):
    query = db.query(Request).options(joinedload(Request.category), joinedload(Request.unit),
                                      joinedload(Request.assignee), joinedload(Request.student))
    target_unit = unit_id if user.role == Role.ADMIN else user.unit_id
    if target_unit:
        query = query.filter(or_(Request.unit_id == target_unit, Request.assignee_id == user.id))
    elif user.role != Role.ADMIN:
        query = query.filter(Request.assignee_id == user.id)
    if mine:
        query = query.filter(Request.assignee_id == user.id)
    hours = sla.policy_hours(db)
    cutoff = utcnow() - timedelta(days=14)
    columns: dict[str, list] = {}
    for col, statuses in KANBAN_COLUMNS.items():
        cq = query.filter(Request.status.in_(statuses))
        if col == "Closed":
            cq = cq.filter(Request.updated_at >= cutoff).order_by(Request.updated_at.desc()).limit(30)
        else:
            # Highest priority first, unit-queue (unassigned) before assigned, then oldest first.
            cq = cq.order_by(Request.priority_score.desc(), Request.assignee_id.isnot(None), Request.created_at.asc())
        columns[col] = [card(r, hours, user) for r in cq.all()]
    return {"columns": columns, "unit_id": target_unit}


@router.get("/{request_id}", response_model=schemas.RequestDetail)
def get_request(request_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return detail(get_request_or_404(db, request_id, user), db, user)


@router.get("/{request_id}/timeline", response_model=list[schemas.TimelineEvent])
def get_timeline(request_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return timeline.build(db, get_request_or_404(db, request_id, user), user)


@router.patch("/{request_id}/status", response_model=schemas.RequestDetail)
def change_status(request_id: str, body: schemas.StatusPatch, db: Session = Depends(get_db),
                  user: User = Depends(require_staff)):
    req = get_request_or_404(db, request_id, user)
    require_staff_access(user, req)
    target = body.status
    text = schemas.sanitize(body.message) if body.message else None
    if target == Status.IN_PROGRESS and req.assignee_id is None and user.role == Role.AGENT:
        req.assignee_id, req.assignee = user.id, user  # taking a card from the unit queue claims it
    _transition_or_409(db, req, target, user, reason="manual", note=text,
                       student_message=text or None)
    if text:
        # The status notification/email already carries this text, so no separate "new reply" alert.
        msg = Message(request_id=req.id, author_id=user.id, body=text, is_internal=False)
        db.add(msg)
        db.flush()
        notifications.queue_push(db, f"request:{req.id}", {"event": "message", "request_id": req.id,
                                                           "message_id": msg.id, "internal": False,
                                                           "author_id": user.id})
        if req.first_response_at is None:
            req.first_response_at = utcnow()
    db.commit()
    return detail(req, db, user)


@router.post("/{request_id}/assign", response_model=schemas.RequestDetail)
def assign(request_id: str, body: schemas.AssignIn, db: Session = Depends(get_db),
           user: User = Depends(require_staff)):
    req = get_request_or_404(db, request_id, user)
    require_staff_access(user, req)
    agent = db.get(User, body.assignee_id)
    if not agent or agent.role not in (Role.AGENT, Role.UNIT_HEAD) or not agent.is_active:
        raise HTTPException(422, "Assignee must be an active agent or unit head")
    if req.unit_id and agent.unit_id != req.unit_id:
        raise HTTPException(422, "Assignee must belong to the request's unit")
    if req.status == Status.NEEDS_REVIEW:
        raise HTTPException(409, {"message": "Confirm the category before assigning"})
    req.assignee_id, req.assignee = agent.id, agent
    agent.last_assigned_at = utcnow()
    db.add(RoutingLog(request_id=req.id, from_unit_id=req.unit_id, to_unit_id=req.unit_id, assignee_id=agent.id,
                      actor_id=user.id, kind="manual", reason=f"manual: assigned to {agent.name} by {user.name}"))
    if agent.id != user.id:
        notifications.notify(db, agent, "assigned", f"Request assigned to you: {req.id}", req.subject, req, email=False)
    notifications.queue_push(db, f"request:{req.id}", {"event": "request_updated", "request_id": req.id})
    if req.unit_id:
        notifications.queue_push(db, f"unit:{req.unit_id}", {"event": "request_updated", "request_id": req.id})
    db.commit()
    return detail(req, db, user)


@router.post("/{request_id}/override", response_model=schemas.RequestDetail, summary="Agent override of AI decision (US9)")
def override(request_id: str, body: schemas.OverrideIn, db: Session = Depends(get_db),
             user: User = Depends(require_staff)):
    req = get_request_or_404(db, request_id, user)
    require_staff_access(user, req)
    if body.category_id is None and body.priority is None and body.unit_id is None:
        raise HTTPException(422, "Nothing to override")
    if body.category_id and not db.get(Category, body.category_id):
        raise HTTPException(422, "Unknown category")
    if body.unit_id and not db.get(Unit, body.unit_id):
        raise HTTPException(422, "Unknown unit")
    try:
        pipeline.override(db, req, user, body.reason, body.category_id, body.priority, body.unit_id)
    except workflow.TransitionNotAllowed as e:
        db.rollback()
        raise HTTPException(409, {"message": "Transition not allowed", "from": e.from_status, "to": e.to_status})
    db.commit()
    return detail(req, db, user)


@router.post("/{request_id}/step", response_model=schemas.RequestDetail, summary="Advance workflow template step")
def advance_step(request_id: str, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    req = get_request_or_404(db, request_id, user)
    require_staff_access(user, req)
    try:
        workflow.advance_step(db, req, user)
    except workflow.TransitionNotAllowed:
        raise HTTPException(409, {"message": "No further workflow step"})
    db.commit()
    return detail(req, db, user)
