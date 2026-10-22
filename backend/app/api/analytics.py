"""Analytics dashboard aggregates (US13). Unit heads and agents are locked to their own unit."""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from statistics import mean

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db, utcnow
from ..models import CSAT, AIFeedback, Category, Priority, Request, Role, Status, SuggestionEvent, Unit, User
from ..security import require_staff

router = APIRouter(prefix="/analytics", tags=["analytics"])


class Filters:
    def __init__(self, date_from: date | None = None, date_to: date | None = None, unit_id: int | None = None,
                 category_id: int | None = None, days: int | None = None, priority: str | None = None,
                 status: str | None = None):
        self.date_from, self.date_to, self.unit_id, self.category_id, self.days = (
            date_from, date_to, unit_id, category_id, days)
        self.priority, self.status = priority, status

    def as_dict(self) -> dict:
        return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in vars(self).items() if v is not None}


def scoped_filters(f: Filters = Depends(), user: User = Depends(require_staff)) -> Filters:
    if user.role != Role.ADMIN:
        if user.unit_id is None:
            raise HTTPException(403, "Access denied")
        f.unit_id = user.unit_id  # locked to own unit
    if f.days and not f.date_from:
        f.date_from = (utcnow() - timedelta(days=f.days - 1)).date()
    return f


def base_query(db: Session, f: Filters):
    q = db.query(Request)
    if f.date_from:
        q = q.filter(Request.created_at >= datetime.combine(f.date_from, datetime.min.time()))
    if f.date_to:
        q = q.filter(Request.created_at < datetime.combine(f.date_to + timedelta(days=1), datetime.min.time()))
    if f.unit_id:
        q = q.filter(Request.unit_id == f.unit_id)
    if f.category_id:
        q = q.filter(Request.category_id == f.category_id)
    if f.priority:
        q = q.filter(Request.priority == f.priority)
    if f.status:
        q = q.filter(Request.status == f.status)
    return q


def _event_query(db: Session, f: Filters):
    q = db.query(SuggestionEvent)
    if f.date_from:
        q = q.filter(SuggestionEvent.created_at >= datetime.combine(f.date_from, datetime.min.time()))
    if f.date_to:
        q = q.filter(SuggestionEvent.created_at < datetime.combine(f.date_to + timedelta(days=1), datetime.min.time()))
    if f.unit_id:
        q = q.filter(SuggestionEvent.unit_id == f.unit_id)
    if f.category_id:
        q = q.filter(SuggestionEvent.category_id == f.category_id)
    return q


def suggestion_kpis(db: Session, f: Filters, total_requests: int) -> dict:
    """Self-service deflection (US20) and smart-reply usage (US19)."""
    deflections = _event_query(db, f).filter(SuggestionEvent.action == "deflected").count()
    shown = {r for (r,) in _event_query(db, f).filter(SuggestionEvent.type == "smart_reply",
                                                      SuggestionEvent.action == "shown")
             .with_entities(SuggestionEvent.request_id).distinct()}
    used = {r for (r,) in _event_query(db, f).filter(SuggestionEvent.type == "smart_reply",
                                                     SuggestionEvent.action.in_(("used", "edited")))
            .with_entities(SuggestionEvent.request_id).distinct()}
    asked = deflections + total_requests
    return {
        "deflections": deflections,
        "deflection_rate": round(100 * deflections / asked, 1) if asked else None,
        "smart_reply_requests": len(shown),
        "smart_reply_usage": round(100 * len(used & shown) / len(shown), 1) if shown else None,
    }


def _hours(a: datetime | None, b: datetime | None) -> float | None:
    return (b - a).total_seconds() / 3600 if a and b else None


def _avg(xs) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(mean(xs), 2) if xs else None


def compute(db: Session, f: Filters) -> dict:
    q = base_query(db, f)
    rows = q.with_entities(Request.id, Request.status, Request.priority, Request.category_id, Request.unit_id,
                           Request.assignee_id, Request.created_at, Request.first_response_at, Request.resolved_at,
                           Request.sla_resolution_due, Request.sla_breached, Request.ai_category_id,
                           Request.ai_keywords).all()
    ids = [r.id for r in rows]
    now = utcnow()

    total = len(rows)
    open_ = sum(r.status in Status.OPEN for r in rows)
    resolved = sum(r.status in (Status.RESOLVED, Status.CLOSED) for r in rows)

    # SLA compliance: of requests whose resolution SLA is decided (resolved, or past due), share met in time.
    decided = met = 0
    by_prio_sla: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in rows:
        if r.sla_resolution_due is None:
            continue
        done = r.resolved_at is not None
        if not done and now < r.sla_resolution_due and not r.sla_breached:
            continue
        ok = done and r.resolved_at <= r.sla_resolution_due and not r.sla_breached
        decided += 1
        met += ok
        by_prio_sla[r.priority][0] += 1
        by_prio_sla[r.priority][1] += ok

    csat_rows = []
    if ids:
        csat_rows = (db.query(CSAT.request_id, CSAT.rating).join(Request, Request.id == CSAT.request_id)
                     .filter(Request.id.in_(base_query(db, f).with_entities(Request.id))).all())
    csat_by_req = {cid: rating for cid, rating in csat_rows}

    classified = [r for r in rows if r.ai_category_id is not None]
    fb = []
    if ids:
        fb = (db.query(AIFeedback.request_id, AIFeedback.predicted_category, AIFeedback.corrected_category)
              .filter(AIFeedback.request_id.in_(base_query(db, f).with_entities(Request.id)),
                      AIFeedback.corrected_category.isnot(None)).all())
    overridden = {x.request_id for x in fb if x.corrected_category != x.predicted_category}
    ai_accuracy = round(100 * (1 - len(overridden) / len(classified)), 1) if classified else None

    cats = {c.id: c.name for c in db.query(Category)}
    units = {u.id: u.name for u in db.query(Unit)}
    agents = {u.id: u.name for u in db.query(User).filter(User.role.in_((Role.AGENT, Role.UNIT_HEAD)))}

    # Requests over time (created vs resolved per day)
    start = f.date_from or (min((r.created_at for r in rows), default=now).date())
    end = f.date_to or now.date()
    created_by_day = Counter(r.created_at.date() for r in rows)
    resolved_by_day = Counter(r.resolved_at.date() for r in rows if r.resolved_at)
    over_time = []
    d = start
    while d <= end and len(over_time) < 400:
        over_time.append({"date": d.isoformat(), "created": created_by_day.get(d, 0), "resolved": resolved_by_day.get(d, 0)})
        d += timedelta(days=1)

    by_category = Counter(cats.get(r.category_id, "Unclassified") for r in rows)

    def group(s: str) -> str:
        if s in (Status.RESOLVED, Status.CLOSED):
            return "resolved"
        if s == Status.IN_PROGRESS:
            return "in_progress"
        if s == Status.WAITING:
            return "waiting"
        return "new"

    by_unit: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        by_unit[units.get(r.unit_id, "Triage / unassigned")][group(r.status)] += 1

    keywords = Counter(k for r in rows for k in (r.ai_keywords or [])[:3])

    lb: dict[int, dict] = defaultdict(lambda: {"resolved": 0, "open": 0, "res_hours": [], "csat": []})
    for r in rows:
        if r.assignee_id is None:
            continue
        e = lb[r.assignee_id]
        if r.status in (Status.RESOLVED, Status.CLOSED):
            e["resolved"] += 1
            e["res_hours"].append(_hours(r.created_at, r.resolved_at))
        elif r.status in Status.OPEN:
            e["open"] += 1
        if r.id in csat_by_req:
            e["csat"].append(csat_by_req[r.id])
    leaderboard = sorted(
        ({"agent_id": aid, "agent": agents.get(aid, f"#{aid}"), "resolved": e["resolved"], "open": e["open"],
          "avg_resolution_hours": _avg(e["res_hours"]), "csat": _avg(e["csat"])} for aid, e in lb.items()),
        key=lambda x: (-x["resolved"], x["avg_resolution_hours"] or 1e9))[:10]

    per_cat_total = Counter(cats.get(r.ai_category_id, "?") for r in classified)
    per_cat_wrong = Counter(x.predicted_category for x in fb if x.request_id in overridden)

    return {
        "filters": {"date_from": f.date_from, "date_to": f.date_to, "unit_id": f.unit_id, "category_id": f.category_id,
                    "priority": f.priority, "status": f.status},
        "kpis": {
            "total": total, "open": open_, "resolved": resolved,
            "avg_first_response_hours": _avg(_hours(r.created_at, r.first_response_at) for r in rows),
            "avg_resolution_hours": _avg(_hours(r.created_at, r.resolved_at) for r in rows),
            "sla_compliance": round(100 * met / decided, 1) if decided else None,
            "csat_avg": _avg(csat_by_req.values()), "csat_count": len(csat_by_req),
            "ai_accuracy": ai_accuracy, "overrides": len(overridden),
            **suggestion_kpis(db, f, total),
        },
        "over_time": over_time,
        "by_category": [{"category": k, "count": v} for k, v in by_category.most_common()],
        "by_unit": [{"unit": k, **{g: c.get(g, 0) for g in ("new", "in_progress", "waiting", "resolved")}}
                    for k, c in sorted(by_unit.items(), key=lambda kv: -sum(kv[1].values()))],
        "priority": [{"priority": p, "count": sum(r.priority == p for r in rows)} for p in reversed(Priority.ORDER)],
        "sla_by_priority": [{"priority": p, "decided": by_prio_sla[p][0],
                             "compliance": round(100 * by_prio_sla[p][1] / by_prio_sla[p][0], 1) if by_prio_sla[p][0] else None}
                            for p in reversed(Priority.ORDER)],
        "top_keywords": [{"keyword": k, "count": v} for k, v in keywords.most_common(12)],
        "leaderboard": leaderboard,
        "ai_by_category": [{"category": c, "classified": n, "overridden": per_cat_wrong.get(c, 0),
                            "accuracy": round(100 * (1 - per_cat_wrong.get(c, 0) / n), 1)}
                           for c, n in per_cat_total.most_common()],
    }


@router.get("/dashboard", summary="All dashboard data in one call")
def dashboard(f: Filters = Depends(scoped_filters), db: Session = Depends(get_db)):
    return compute(db, f)


@router.get("/summary")
def summary(f: Filters = Depends(scoped_filters), db: Session = Depends(get_db)):
    return compute(db, f)["kpis"]


@router.get("/by-category")
def by_category(f: Filters = Depends(scoped_filters), db: Session = Depends(get_db)):
    return compute(db, f)["by_category"]


@router.get("/by-unit")
def by_unit(f: Filters = Depends(scoped_filters), db: Session = Depends(get_db)):
    return compute(db, f)["by_unit"]


@router.get("/sla")
def sla_stats(f: Filters = Depends(scoped_filters), db: Session = Depends(get_db)):
    data = compute(db, f)
    return {"compliance": data["kpis"]["sla_compliance"], "by_priority": data["sla_by_priority"]}


@router.get("/ai-accuracy")
def ai_accuracy(f: Filters = Depends(scoped_filters), db: Session = Depends(get_db)):
    data = compute(db, f)
    return {"accuracy": data["kpis"]["ai_accuracy"], "overrides": data["kpis"]["overrides"],
            "by_category": data["ai_by_category"]}
