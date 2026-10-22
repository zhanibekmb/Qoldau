"""SLA timers & auto-escalation (US12).

Due dates are set when a request is routed. While status = "Waiting for Student" the clock is
paused; on resume both due dates are pushed forward by the paused duration.
A scheduler tick (every minute) sends the 80% warning and escalates breaches to the unit head.
"""
import re
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..db import utcnow
from ..models import Escalation, Priority, Request, Role, SLAPolicy, Status, Unit, User
from . import notifications, urgency

DEFAULT_POLICIES = {
    Priority.CRITICAL: (1, 8),
    Priority.HIGH: (4, 24),
    Priority.MEDIUM: (24, 72),
    Priority.LOW: (48, 120),
}
LOCAL_UTC_OFFSET = timedelta(hours=5)  # Asia/Almaty; working hours are local time
_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_WH_RE = re.compile(r"(?i)(mon|tue|wed|thu|fri|sat|sun)\s*-\s*(mon|tue|wed|thu|fri|sat|sun)\s+(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")


def policy_for(db: Session, priority: str) -> tuple[float, float, bool]:
    p = db.query(SLAPolicy).filter_by(priority=priority).first()
    if p:
        return p.first_response_hours, p.resolution_hours, p.use_working_hours
    fr, res = DEFAULT_POLICIES[priority]
    return fr, res, False


def add_hours(start: datetime, hours: float, working_hours: str | None, use_working_hours: bool) -> datetime:
    """Add SLA hours, counting only the unit's working hours when configured (e.g. "Mon-Fri 09:00-18:00")."""
    if not use_working_hours or not working_hours or not (m := _WH_RE.search(working_hours)):
        return start + timedelta(hours=hours)
    d0, d1 = _DAYS.index(m.group(1).lower()), _DAYS.index(m.group(2).lower())
    open_t = timedelta(hours=int(m.group(3)), minutes=int(m.group(4)))
    close_t = timedelta(hours=int(m.group(5)), minutes=int(m.group(6)))
    remaining = timedelta(hours=hours)
    cur = start + LOCAL_UTC_OFFSET
    for _ in range(3660):  # hard stop: ~10 years of days
        day_start = cur.replace(hour=0, minute=0, second=0, microsecond=0)
        if d0 <= cur.weekday() <= d1:
            window_open, window_close = day_start + open_t, day_start + close_t
            if cur < window_open:
                cur = window_open
            if cur < window_close:
                available = window_close - cur
                if remaining <= available:
                    return cur + remaining - LOCAL_UTC_OFFSET
                remaining -= available
        cur = day_start + timedelta(days=1)
    return start + timedelta(hours=hours)


def assign_due_dates(db: Session, req: Request, start: datetime | None = None) -> None:
    start = start or utcnow()
    fr, res, use_wh = policy_for(db, req.priority)
    wh = req.unit.working_hours if req.unit else None
    if req.first_response_at is None:
        req.sla_first_response_due = add_hours(start, fr, wh, use_wh)
    req.sla_resolution_due = add_hours(start, res, wh, use_wh)
    req.sla_warned = False


def pause(req: Request, now: datetime | None = None) -> None:
    if req.sla_paused_at is None:
        req.sla_paused_at = now or utcnow()


def resume(req: Request, now: datetime | None = None) -> None:
    if req.sla_paused_at is None:
        return
    paused_for = (now or utcnow()) - req.sla_paused_at
    if req.sla_first_response_due and req.first_response_at is None:
        req.sla_first_response_due += paused_for
    if req.sla_resolution_due:
        req.sla_resolution_due += paused_for
    req.sla_paused_at = None


def active_target(req: Request) -> tuple[str, datetime | None]:
    if req.first_response_at is None:
        return "first_response", req.sla_first_response_due
    return "resolution", req.sla_resolution_due


def state(hours: tuple[float, float], req: Request, now: datetime | None = None) -> dict | None:
    """SLA badge data for the UI: colour green > 50% left, yellow 20-50%, red < 20%, black = breached."""
    if req.status in (Status.RESOLVED, Status.CLOSED) or req.unit_id is None:
        return None
    target, due = active_target(req)
    if due is None:
        return None
    now = req.sla_paused_at or now or utcnow()
    fr, res = hours
    total = timedelta(hours=fr if target == "first_response" else res).total_seconds()
    remaining = (due - now).total_seconds()
    frac = remaining / total if total else 0
    color = "black" if remaining <= 0 else "red" if frac <= 0.2 else "yellow" if frac <= 0.5 else "green"
    return {
        "target": target,
        "due_at": due,
        "remaining_seconds": int(remaining),
        "remaining_fraction": round(max(frac, 0), 3),
        "color": color,
        "paused": req.sla_paused_at is not None,
        "breached": remaining <= 0 or req.sla_breached,
    }


def policy_hours(db: Session) -> dict[str, tuple[float, float]]:
    out = {k: (v[0], v[1]) for k, v in DEFAULT_POLICIES.items()}
    for p in db.query(SLAPolicy).all():
        out[p.priority] = (p.first_response_hours, p.resolution_hours)
    return out


def _unit_staff(db: Session, unit_id: int, roles: tuple[str, ...]) -> list[User]:
    return db.query(User).filter(User.unit_id == unit_id, User.role.in_(roles), User.is_active.is_(True)).all()


def _unit_head(db: Session, unit_id: int) -> User | None:
    unit = db.get(Unit, unit_id)
    if unit and unit.head_user_id:
        return db.get(User, unit.head_user_id)
    heads = _unit_staff(db, unit_id, (Role.UNIT_HEAD,))
    return heads[0] if heads else None


def _already(db: Session, req: Request, kind: str, target: str) -> bool:
    return db.query(Escalation.id).filter_by(request_id=req.id, kind=kind, target=target).first() is not None


def check_request(db: Session, req: Request, hours: dict, now: datetime) -> list[str]:
    """Apply warning/breach rules to one request; returns the actions taken."""
    if req.status not in Status.OPEN or req.status == Status.WAITING or req.sla_paused_at or req.unit_id is None:
        return []
    target, due = active_target(req)
    if due is None:
        return []
    fr, res = hours[req.priority]
    total = timedelta(hours=fr if target == "first_response" else res)
    elapsed_frac = 1 - (due - now) / total
    actions = []
    label = "first response" if target == "first_response" else "resolution"

    if elapsed_frac >= 0.8 and not _already(db, req, "sla_warning", target):
        recipients = [req.assignee] if req.assignee else _unit_staff(db, req.unit_id, (Role.AGENT,))
        for u in recipients:
            notifications.notify(db, u, "sla_warning", f"SLA warning: {req.id}",
                                 f"80% of the {label} SLA has elapsed (due {due:%Y-%m-%d %H:%M} UTC).", req)
        db.add(Escalation(request_id=req.id, kind="sla_warning", target=target,
                          notified_user_id=recipients[0].id if recipients else None,
                          detail=f"{label} SLA 80% elapsed"))
        req.sla_warned = True
        actions.append("warning")

    if now >= due and not _already(db, req, "sla_breach", target):
        old_priority = req.priority
        req.priority = urgency.raise_one_level(req.priority)
        req.priority_score = max(req.priority_score, {"Low": 35, "Medium": 60, "High": 80, "Critical": 80}[old_priority])
        req.sla_breached = True
        req.escalated = True
        head = _unit_head(db, req.unit_id)
        detail = f"{label} SLA breached; priority {old_priority} -> {req.priority}"
        if head:
            notifications.notify(db, head, "sla_breach", f"Escalated: {req.id} breached SLA", detail, req)
        if req.assignee and (not head or req.assignee.id != head.id):
            notifications.notify(db, req.assignee, "sla_breach", f"SLA breached: {req.id}", detail, req, email=False)
        db.add(Escalation(request_id=req.id, kind="sla_breach", target=target,
                          notified_user_id=head.id if head else None, detail=detail))
        actions.append("breach")

    if actions:
        notifications.queue_push(db, f"unit:{req.unit_id}", {"event": "request_updated", "request_id": req.id})
    return actions


def run_tick(db: Session, now: datetime | None = None) -> dict:
    """Scheduler job: SLA warnings/escalations + auto-close of resolved requests."""
    from . import workflow  # local import to avoid a cycle

    now = now or utcnow()
    hours = policy_hours(db)
    summary = {"warnings": 0, "breaches": 0, "closed": 0}
    open_reqs = db.query(Request).filter(Request.status.in_(Status.OPEN), Request.status != Status.WAITING,
                                         Request.unit_id.isnot(None)).all()
    for req in open_reqs:
        for a in check_request(db, req, hours, now):
            summary["warnings" if a == "warning" else "breaches"] += 1

    cutoff = now - timedelta(days=7)
    for req in db.query(Request).filter(Request.status == Status.RESOLVED, Request.resolved_at <= cutoff).all():
        workflow.transition(db, req, Status.CLOSED, actor=None, reason="system", note="Auto-closed 7 days after resolution")
        summary["closed"] += 1
    db.commit()
    return summary
