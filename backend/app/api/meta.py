"""Read-only directory data for forms (category dropdown, override panel, assignee picker)."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import Category, Role, SLAPolicy, Unit, User
from ..security import current_user, require_staff
from ..services import routing, sla, workflow

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/public")
def public_service(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    settings = get_settings()
    publish = settings.pilot_directory_published
    directories = db.query(Unit).order_by(Unit.id).all() if publish else []
    policies = {policy.priority: policy for policy in db.query(SLAPolicy)} if publish else {}
    return {
        "support_email": settings.pilot_support_email,
        "privacy_url": settings.pilot_privacy_url or None,
        "data_contact": settings.pilot_data_contact,
        "attachments_enabled": settings.effective_attachment_mode != "disabled",
        "max_upload_mb": settings.max_upload_mb,
        "offices": [{"id": unit.id, "name": unit.name, "email": unit.email, "working_hours": unit.working_hours,
                     "is_triage": unit.is_triage} for unit in directories],
        "sla": [
            {"priority": policy.priority, "first_response_hours": policy.first_response_hours,
             "resolution_hours": policy.resolution_hours, "use_working_hours": policy.use_working_hours}
            for priority in sla.DEFAULT_POLICIES if (policy := policies.get(priority)) is not None
        ],
    }


@router.get("/categories")
def categories(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return [{"id": c.id, "name": c.name, "unit_id": c.unit_id, "default_workflow": c.default_workflow}
            for c in db.query(Category).filter_by(is_active=True).order_by(Category.id)]


@router.get("/units")
def units(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return [{"id": u.id, "name": u.name, "is_triage": u.is_triage} for u in db.query(Unit).order_by(Unit.id)]


@router.get("/agents")
def agents(unit_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    q = db.query(User).filter(User.role.in_((Role.AGENT, Role.UNIT_HEAD)), User.is_active.is_(True))
    if unit_id:
        q = q.filter(User.unit_id == unit_id)
    users = q.order_by(User.name).all()
    counts = routing.open_ticket_counts(db, [u.id for u in users]) if users else {}
    return [{"id": u.id, "name": u.name, "role": u.role, "unit_id": u.unit_id, "online": routing.is_online(u),
             "open_tickets": counts.get(u.id, 0)} for u in users]


@router.get("/workflow")
def workflow_info(_: User = Depends(current_user)):
    return {"transitions": {k: sorted(v) for k, v in workflow.ALLOWED.items()}, "templates": workflow.TEMPLATES}
