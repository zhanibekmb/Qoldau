"""Admin configuration panel API (US14). Admin role only; every change is written to audit_log."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import schemas
from ..db import Base, get_db, utcnow
from ..models import (AuditLog, Category, EmailOutbox, PasswordResetToken, Request, Role, RoutingRule, SLAPolicy,
                      Status, Unit, UrgencyKeyword, User)
from ..security import hash_new_password, require_admin
from ..services import sla

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

SECRET_FIELDS = {"password_hash"}


def snapshot(obj: Base) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns if c.name not in SECRET_FIELDS}


def _json_safe(d: dict | None) -> dict | None:
    if d is None:
        return None
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in d.items()}


def audit(db: Session, actor: User, entity: str, entity_id, action: str, old: dict | None, new: dict | None) -> None:
    db.add(AuditLog(actor_id=actor.id, entity=entity, entity_id=str(entity_id), action=action,
                    old=_json_safe(old), new=_json_safe(new)))


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, {"message": "Duplicate or invalid reference"})


def _get(db: Session, model, obj_id: int):
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(404, "Not found")
    return obj


def crud(entity: str, model, in_schema, out_schema, path: str, before_delete=None, after_write=None):
    """Register list/create/update/delete endpoints for a simple config entity."""

    @router.get(f"/{path}", response_model=list[out_schema], name=f"list_{path}")
    def list_items(db: Session = Depends(get_db)):
        return [out_schema.model_validate(o) for o in db.query(model).order_by(model.id).all()]

    @router.post(f"/{path}", response_model=out_schema, status_code=201, name=f"create_{path}")
    def create_item(body: in_schema, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
        obj = model(**body.model_dump())
        db.add(obj)
        db.flush()
        if after_write:
            after_write(db, obj)
        audit(db, admin, entity, obj.id, "create", None, snapshot(obj))
        _commit(db)
        return out_schema.model_validate(obj)

    @router.put(f"/{path}/{{obj_id}}", response_model=out_schema, name=f"update_{path}")
    def update_item(obj_id: int, body: in_schema, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
        obj = _get(db, model, obj_id)
        old = snapshot(obj)
        for k, v in body.model_dump().items():
            setattr(obj, k, v)
        db.flush()
        if after_write:
            after_write(db, obj)
        audit(db, admin, entity, obj.id, "update", old, snapshot(obj))
        _commit(db)
        return out_schema.model_validate(obj)

    @router.delete(f"/{path}/{{obj_id}}", status_code=204, name=f"delete_{path}")
    def delete_item(obj_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
        obj = _get(db, model, obj_id)
        if before_delete:
            before_delete(db, obj)
        audit(db, admin, entity, obj.id, "delete", snapshot(obj), None)
        db.delete(obj)
        _commit(db)


def _unit_guard(db: Session, unit: Unit) -> None:
    n = db.query(Request).filter(Request.unit_id == unit.id, Request.status.in_(Status.OPEN)).count()
    if n:
        raise HTTPException(409, {"message": f"Unit has {n} open requests; reassign them before deleting"})


def _validate_unit(db: Session, unit: Unit) -> None:
    if not sla.parse_working_hours(unit.working_hours):
        raise HTTPException(422, {"message": "Use working hours in the format Mon-Fri 09:00-18:00"})
    if unit.head_user_id is not None:
        head = db.get(User, unit.head_user_id)
        if not head or not head.is_active or head.role != Role.UNIT_HEAD or head.unit_id != unit.id:
            raise HTTPException(422, {"message": "Select an active unit head from this office"})
    if unit.is_triage and db.query(Unit.id).filter(Unit.is_triage.is_(True), Unit.id != unit.id).first():
        raise HTTPException(409, {"message": "One office can be marked as the Triage queue"})


def _category_guard(db: Session, cat: Category) -> None:
    if db.query(Request).filter(Request.category_id == cat.id).count():
        raise HTTPException(409, {"message": "Category is used by requests; deactivate it instead"})


def _one_active_rule(db: Session, rule: RoutingRule) -> None:
    if rule.is_active:
        (db.query(RoutingRule).filter(RoutingRule.category_id == rule.category_id, RoutingRule.id != rule.id,
                                      RoutingRule.is_active.is_(True)).update({RoutingRule.is_active: False}))


crud("category", Category, schemas.CategoryIn, schemas.CategoryOut, "categories", before_delete=_category_guard)
crud("unit", Unit, schemas.UnitIn, schemas.UnitOut, "units", before_delete=_unit_guard, after_write=_validate_unit)
crud("sla_policy", SLAPolicy, schemas.SLAPolicyIn, schemas.SLAPolicyOut, "sla-policies")
crud("urgency_keyword", UrgencyKeyword, schemas.KeywordIn, schemas.KeywordOut, "keywords")


# Routing rules get names joined in for the UI, so they are written out explicitly.
def _rule_out(r: RoutingRule) -> schemas.RoutingRuleOut:
    out = schemas.RoutingRuleOut.model_validate(r)
    out.category_name, out.unit_name = r.category.name, r.unit.name
    return out


@router.get("/routing-rules", response_model=list[schemas.RoutingRuleOut])
def list_rules(db: Session = Depends(get_db)):
    return [_rule_out(r) for r in db.query(RoutingRule).order_by(RoutingRule.id.desc()).all()]


@router.post("/routing-rules", response_model=schemas.RoutingRuleOut, status_code=201)
def create_rule(body: schemas.RoutingRuleIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    _get(db, Category, body.category_id)
    _get(db, Unit, body.unit_id)
    rule = RoutingRule(**body.model_dump())
    db.add(rule)
    db.flush()
    _one_active_rule(db, rule)
    db.refresh(rule)
    audit(db, admin, "routing_rule", rule.id, "create", None,
          {**snapshot(rule), "rule": f"{rule.category.name} -> {rule.unit.name}"})
    _commit(db)
    return _rule_out(rule)


@router.put("/routing-rules/{obj_id}", response_model=schemas.RoutingRuleOut)
def update_rule(obj_id: int, body: schemas.RoutingRuleIn, db: Session = Depends(get_db),
                admin: User = Depends(require_admin)):
    rule = _get(db, RoutingRule, obj_id)
    _get(db, Category, body.category_id)
    _get(db, Unit, body.unit_id)
    old = snapshot(rule)
    for k, v in body.model_dump().items():
        setattr(rule, k, v)
    db.flush()
    _one_active_rule(db, rule)
    db.refresh(rule)
    audit(db, admin, "routing_rule", rule.id, "update", old,
          {**snapshot(rule), "rule": f"{rule.category.name} -> {rule.unit.name}"})
    _commit(db)
    return _rule_out(rule)


@router.delete("/routing-rules/{obj_id}", status_code=204)
def delete_rule(obj_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rule = _get(db, RoutingRule, obj_id)
    audit(db, admin, "routing_rule", rule.id, "delete", snapshot(rule), None)
    db.delete(rule)
    _commit(db)


# Users & roles
def _user_out(u: User) -> schemas.UserOut:
    out = schemas.UserOut.model_validate(u)
    out.unit_name = u.unit.name if u.unit else None
    return out


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db), role: str | None = None, q: str | None = Query(None, max_length=100)):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if q:
        query = query.filter(User.name.ilike(f"%{q}%") | User.email.ilike(f"%{q}%"))
    return [_user_out(u) for u in query.order_by(User.role, User.name).limit(500)]


@router.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(body: schemas.UserIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if not body.password:
        raise HTTPException(422, "Password is required for new users")
    data = body.model_dump(exclude={"password"})
    data["email"] = data["email"].lower()
    user = User(**data, password_hash=hash_new_password(body.password), must_change_password=True)
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, {"message": "Duplicate or invalid reference"})
    audit(db, admin, "user", user.id, "create", None, snapshot(user))
    _commit(db)
    return _user_out(user)


@router.put("/users/{obj_id}", response_model=schemas.UserOut)
def update_user(obj_id: int, body: schemas.UserIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = _get(db, User, obj_id)
    if user.id == admin.id and (body.role != Role.ADMIN or not body.is_active):
        raise HTTPException(409, {"message": "You cannot remove your own admin access"})
    old = snapshot(user)
    data = body.model_dump(exclude={"password"})
    data["email"] = data["email"].lower()
    access_fields = ("is_active", "role", "unit_id", "email")
    if body.password or any(data[key] != old[key] for key in access_fields):
        data.update(session_version=User.session_version + 1, last_seen_at=None)
    if body.password:
        data.update(password_hash=hash_new_password(body.password), must_change_password=True)
    try:
        changed = db.execute(update(User).where(User.id == obj_id, User.session_version == user.session_version)
                             .values(**data))
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, {"message": "Duplicate or invalid reference"})
    if changed.rowcount != 1:
        raise HTTPException(409, "Account changed. Refresh and try again")
    if body.password or any(data[key] != old[key] for key in access_fields):
        now = utcnow()
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == obj_id,
                                            PasswordResetToken.used_at.is_(None)).update(
            {PasswordResetToken.used_at: now}, synchronize_session=False)
        db.query(EmailOutbox).filter(EmailOutbox.user_id == obj_id,
                                     EmailOutbox.kind == "password_reset",
                                     EmailOutbox.status == "queued").update(
            {EmailOutbox.status: "failed", EmailOutbox.last_error: "superseded",
             EmailOutbox.next_attempt_at: None}, synchronize_session=False)
    db.refresh(user)
    audit(db, admin, "user", user.id, "update", old, {**snapshot(user), **({"password": "changed"} if body.password else {})})
    _commit(db)
    return _user_out(user)


@router.get("/audit-log", response_model=list[schemas.AuditOut])
def audit_log(db: Session = Depends(get_db), entity: str | None = None, limit: int = Query(100, le=500)):
    q = db.query(AuditLog)
    if entity:
        q = q.filter(AuditLog.entity == entity)
    return q.order_by(AuditLog.id.desc()).limit(limit).all()
