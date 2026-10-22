"""Read-only directory data for forms (category dropdown, override panel, assignee picker)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Category, Role, Unit, User
from ..security import current_user, require_staff
from ..services import routing, workflow

router = APIRouter(prefix="/meta", tags=["meta"])


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
