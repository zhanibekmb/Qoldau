"""Shared access rules and serializers for request endpoints."""
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from .. import schemas
from ..models import Request, Role, Status, Unit, User
from ..services import sla, workflow


def visibility_filter(q: Query, user: User, db: Session) -> Query:
    if user.role == Role.STUDENT:
        return q.filter(Request.student_id == user.id)
    if user.role == Role.ADMIN:
        return q
    triage_ids = [u.id for u in db.query(Unit).filter_by(is_triage=True)]
    return q.filter(or_(Request.unit_id == user.unit_id, Request.assignee_id == user.id,
                        Request.status == Status.NEEDS_REVIEW, Request.unit_id.in_(triage_ids)))


def can_view(user: User, req: Request) -> bool:
    if user.role == Role.STUDENT:
        return req.student_id == user.id
    if user.role == Role.ADMIN:
        return True
    return (req.unit_id == user.unit_id or req.assignee_id == user.id or req.status == Status.NEEDS_REVIEW
            or (req.unit is not None and req.unit.is_triage))


def get_request_or_404(db: Session, request_id: str, user: User) -> Request:
    req = db.get(Request, request_id.strip().upper())
    if req is None or not can_view(user, req):
        # Do not reveal that another student's request exists.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    return req


def require_staff_access(user: User, req: Request) -> None:
    if user.role not in Role.STAFF or not can_view(user, req):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")


def _brief(obj, cls):
    return cls.model_validate(obj) if obj is not None else None


def card(req: Request, hours: dict, viewer: User) -> schemas.RequestCard:
    return schemas.RequestCard(
        id=req.id, subject=req.subject, status=req.status, priority=req.priority, priority_score=req.priority_score,
        category=_brief(req.category, schemas.CategoryBrief), unit=_brief(req.unit, schemas.UnitBrief),
        assignee=_brief(req.assignee, schemas.UserBrief),
        student=_brief(req.student, schemas.UserBrief) if viewer.role in Role.STAFF else None,
        ai_confidence=req.ai_confidence, escalated=req.escalated,
        sla=sla.state(hours[req.priority], req), created_at=req.created_at, updated_at=req.updated_at,
    )


def detail(req: Request, db: Session, viewer: User) -> schemas.RequestDetail:
    hours = sla.policy_hours(db)
    base = card(req, hours, viewer).model_dump()
    staff = viewer.role in Role.STAFF
    ai = None
    if staff:
        from ..models import Category
        student_cat = db.get(Category, req.student_category_id) if req.student_category_id else None
        predicted_unit = None
        if req.ai_category is not None:
            from ..services.routing import resolve_unit
            predicted_unit, _ = resolve_unit(db, req.ai_category)
        ai = schemas.AIDecision(
            predicted_category=_brief(req.ai_category, schemas.CategoryBrief), confidence=req.ai_confidence,
            alternatives=req.ai_alternatives or [], keywords=req.ai_keywords or [],
            predicted_priority=req.ai_priority, priority_reasons=req.priority_reasons or [],
            predicted_unit=_brief(predicted_unit, schemas.UnitBrief),
            student_category=_brief(student_cat, schemas.CategoryBrief), model_version=req.model_version,
        )
    return schemas.RequestDetail(
        **base, description=req.description, workflow=req.workflow,
        workflow_steps=workflow.TEMPLATES.get(req.workflow, []), workflow_step=req.workflow_step,
        first_response_at=req.first_response_at, resolved_at=req.resolved_at,
        csat=schemas.CSATOut.model_validate(req.csat) if req.csat else None,
        allowed_transitions=sorted(workflow.ALLOWED.get(req.status, set())) if staff else [],
        ai=ai,
    )
