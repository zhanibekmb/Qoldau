"""Smart routing (US7): category -> unit via routing_rules, then least-loaded online agent."""
from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import utcnow
from ..models import Category, Request, Role, RoutingLog, RoutingRule, Status, Unit, User
from .realtime import hub

OPEN_FOR_LOAD = (Status.ROUTED, Status.IN_PROGRESS, Status.WAITING, Status.REOPENED)


def triage_unit(db: Session) -> Unit | None:
    return db.query(Unit).filter_by(is_triage=True).first()


def resolve_unit(db: Session, category: Category | None) -> tuple[Unit | None, str]:
    if category is None:
        unit = triage_unit(db)
        return unit, "rule: no category -> triage"
    rule = (db.query(RoutingRule).filter_by(category_id=category.id, is_active=True)
            .order_by(RoutingRule.id.desc()).first())
    if rule:
        return rule.unit, f"rule: {category.name} -> {rule.unit.name}"
    if category.unit:
        return category.unit, f"rule: {category.name} -> {category.unit.name} (category default)"
    unit = triage_unit(db)
    return unit, f"rule: {category.name} has no rule -> triage"


def is_online(user: User) -> bool:
    if hub.is_online(user.id):
        return True
    window = timedelta(minutes=get_settings().online_window_minutes)
    return user.last_seen_at is not None and utcnow() - user.last_seen_at <= window


def open_ticket_counts(db: Session, user_ids: list[int]) -> dict[int, int]:
    rows = (db.query(Request.assignee_id, func.count(Request.id))
            .filter(Request.assignee_id.in_(user_ids), Request.status.in_(OPEN_FOR_LOAD))
            .group_by(Request.assignee_id).all())
    counts = {uid: 0 for uid in user_ids}
    counts.update({uid: n for uid, n in rows})
    return counts


def pick_agent(db: Session, unit: Unit) -> User | None:
    """Least open tickets wins; ties go to whoever was assigned longest ago (round-robin)."""
    agents = [u for u in db.query(User).filter(User.unit_id == unit.id, User.role == Role.AGENT,
                                               User.is_active.is_(True)).all() if is_online(u)]
    if not agents:
        return None
    counts = open_ticket_counts(db, [a.id for a in agents])
    agents.sort(key=lambda a: (counts[a.id], a.last_assigned_at or utcnow().replace(year=2000), a.id))
    return agents[0]


def route(db: Session, req: Request, actor: User | None = None, kind: str = "rule",
          reason_override: str | None = None, unit: Unit | None = None) -> RoutingLog:
    """Set unit + assignee for a request and log the decision. Does not change status."""
    from_unit = req.unit_id
    if unit is None:
        unit, reason = resolve_unit(db, req.category)
    else:
        reason = f"manual: -> {unit.name}"
    req.unit_id = unit.id if unit else None
    req.unit = unit
    agent = pick_agent(db, unit) if unit and not unit.is_triage else None
    req.assignee_id = agent.id if agent else None
    req.assignee = agent
    if agent:
        agent.last_assigned_at = utcnow()
        reason += f"; assigned to {agent.name} (least open tickets)"
    else:
        reason += "; no agent online -> unit queue"
    entry = RoutingLog(request_id=req.id, from_unit_id=from_unit, to_unit_id=req.unit_id,
                       assignee_id=req.assignee_id, actor_id=actor.id if actor else None,
                       reason=reason_override or reason, kind=kind)
    db.add(entry)
    return entry
