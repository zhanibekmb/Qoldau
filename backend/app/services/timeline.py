"""Unified request timeline (US2 / US11) from status_history, routing_log, messages, escalations and CSAT."""
from sqlalchemy.orm import Session

from .. import schemas
from ..models import CSAT, Escalation, Message, Request, Role, RoutingLog, Status, StatusHistory, User

# Notes containing these markers are agent-internal and are rewritten for students.
_INTERNAL_MARKER = " | reason: "


def build(db: Session, req: Request, viewer: User) -> list[schemas.TimelineEvent]:
    staff = viewer.role in Role.STAFF
    events: list[schemas.TimelineEvent] = []

    for h in db.query(StatusHistory).filter_by(request_id=req.id).order_by(StatusHistory.id).limit(500):
        actor = h.actor.name if h.actor else ("AI" if h.reason == "AI" else "System")
        note = h.note
        if h.from_status is None:
            events.append(schemas.TimelineEvent(id=f"h{h.id}", kind="submitted", title="Submitted", status=h.to_status,
                                                actor=actor, created_at=h.created_at))
            continue
        if h.from_status == h.to_status:
            # Non-status events stored in history: corrections and workflow steps.
            if note and note.startswith("Workflow step:"):
                events.append(schemas.TimelineEvent(id=f"h{h.id}", kind="step", title=note.split(":", 1)[1].strip(),
                                                    actor=actor, created_at=h.created_at))
                continue
            title = note.split(_INTERNAL_MARKER)[0] if note else "Updated"
            short = title.split(":")[0]  # "Category corrected by agent"
            events.append(schemas.TimelineEvent(
                id=f"h{h.id}", kind="ai", title=title if staff else short,
                detail=note.split(_INTERNAL_MARKER)[1] if staff and note and _INTERNAL_MARKER in note else None,
                actor=actor, internal=False, created_at=h.created_at))
            continue
        kind = "ai" if h.to_status in (Status.CLASSIFIED, Status.NEEDS_REVIEW) else "status"
        detail = note
        if not staff and h.to_status == Status.NEEDS_REVIEW:
            detail = "Your request needs a quick review by Student Services."
        if not staff and h.to_status == Status.ROUTED and note:
            detail = None  # routing internals (agent load) are staff-only; unit shown via routing event
        if not staff and note and _INTERNAL_MARKER in note:
            detail = note.split(_INTERNAL_MARKER)[0]
        events.append(schemas.TimelineEvent(id=f"h{h.id}", kind=kind, title=h.to_status, status=h.to_status,
                                            detail=detail, actor=actor, created_at=h.created_at))

    for r in db.query(RoutingLog).filter_by(request_id=req.id).order_by(RoutingLog.id):
        unit = r.to_unit.name if r.to_unit else "Triage queue"
        title = f"Routed to {unit}"
        if r.assignee:
            title += f" · {r.assignee.name}"
        events.append(schemas.TimelineEvent(id=f"r{r.id}", kind="routing", title=title,
                                            detail=r.reason if staff else None,
                                            actor="System" if r.kind == "rule" else "Agent", created_at=r.created_at))

    msgs = db.query(Message).filter_by(request_id=req.id)
    if not staff:
        msgs = msgs.filter(Message.is_internal.is_(False))
    for m in msgs.order_by(Message.id):
        files = ", ".join(a.filename for a in m.attachments)
        events.append(schemas.TimelineEvent(
            id=f"m{m.id}", kind="note" if m.is_internal else "message",
            title="Internal note" if m.is_internal else f"Message from {m.author.name}",
            detail=(m.body + (f" [{files}]" if files else "")).strip(), actor=m.author.name,
            internal=m.is_internal, created_at=m.created_at))

    if staff:
        for e in db.query(Escalation).filter_by(request_id=req.id).order_by(Escalation.id):
            title = {"sla_warning": "SLA warning (80%)", "sla_breach": "SLA breached - escalated",
                     "critical": "Critical alert sent", "low_csat": "Low CSAT - reopened"}.get(e.kind, e.kind)
            events.append(schemas.TimelineEvent(id=f"e{e.id}", kind="escalation", title=title, detail=e.detail,
                                                actor="System", created_at=e.created_at))

    c = db.query(CSAT).filter_by(request_id=req.id).first()
    if c:
        events.append(schemas.TimelineEvent(id=f"c{c.id}", kind="csat", title=f"Rated {c.rating}/5",
                                            detail=c.comment or None, actor=req.student.name, created_at=c.created_at))

    order = {"submitted": 0, "ai": 1, "status": 2, "routing": 3}
    events.sort(key=lambda e: (e.created_at, order.get(e.kind, 4), e.id))
    return events
