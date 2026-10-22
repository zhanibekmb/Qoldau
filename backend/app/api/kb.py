"""Knowledge base: FAQ articles and reply templates (US21).

Staff can read everything. Agents create drafts only ("Propose FAQ"); only an Admin or the Unit Head
of the article's unit can publish or archive (HTTP 403 otherwise). Every content edit stores a row in
faq_article_versions, every action is written to audit_log, and publishing re-indexes the
article's embedding in the background so it reaches student suggestions within seconds.
"""
import html
import math
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from .. import schemas
from ..db import get_db, utcnow
from ..ml import embeddings, pii
from ..models import Category, FAQArticle, FAQArticleVersion, ReplyTemplate, Role, Status, Unit, User
from ..security import current_user, require_staff
from ..services import jobs, notifications
from .admin import audit, snapshot
from .common import get_request_or_404, require_staff_access

router = APIRouter(tags=["knowledge base"])

VERSIONED = ("title", "body", "category_id", "language", "tags")


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
    return slug if len(slug) >= 3 else f"faq-{uuid.uuid4().hex[:8]}"


def _faq_out(a: FAQArticle) -> schemas.FAQOut:
    out = schemas.FAQOut.model_validate(a)
    out.category_name = a.category.name if a.category else None
    out.unit_name = a.unit.name if a.unit else None
    votes = a.helpful_yes + a.helpful_no
    out.helpful_pct = round(100 * a.helpful_yes / votes, 1) if votes else None
    out.author = schemas.UserBrief.model_validate(a.author) if a.author else None
    return out


def _template_out(t: ReplyTemplate) -> schemas.TemplateOut:
    out = schemas.TemplateOut.model_validate(t)
    out.category_name = t.category.name if t.category else None
    out.unit_name = t.unit.name if t.unit else None
    return out


def _get_faq(db: Session, article_id: int) -> FAQArticle:
    a = db.get(FAQArticle, article_id)
    if a is None:
        raise HTTPException(404, "Article not found")
    return a


def can_publish(user: User, unit_id: int | None) -> bool:
    return user.role == Role.ADMIN or (user.role == Role.UNIT_HEAD and unit_id is not None and user.unit_id == unit_id)


def _can_edit(user: User, a: FAQArticle) -> bool:
    return can_publish(user, a.unit_id) or (a.status == "draft" and a.author_id == user.id)


def _scope_unit(db: Session, user: User, unit_id: int | None, category_id: int | None) -> int | None:
    """Admins choose any unit; everyone else writes for their own unit."""
    if category_id is not None and db.get(Category, category_id) is None:
        raise HTTPException(422, "Unknown category")
    if user.role != Role.ADMIN:
        return user.unit_id
    if unit_id is not None:
        if db.get(Unit, unit_id) is None:
            raise HTTPException(422, "Unknown unit")
        return unit_id
    cat = db.get(Category, category_id) if category_id else None
    return cat.unit_id if cat else None


def _save_version(db: Session, a: FAQArticle, editor: User) -> None:
    db.add(FAQArticleVersion(article_id=a.id, version=a.version, title=a.title, body=a.body,
                             category_id=a.category_id, language=a.language, tags=list(a.tags or []),
                             status=a.status, editor_id=editor.id))


def _notify_heads(db: Session, a: FAQArticle, author: User) -> None:
    unit = db.get(Unit, a.unit_id) if a.unit_id else None
    head = db.get(User, unit.head_user_id) if unit and unit.head_user_id else None
    if head and head.id != author.id:
        notifications.notify(db, head, "faq_proposed", f"FAQ draft to review: {a.title}",
                             f"{author.name} proposed a new FAQ article ({a.language.upper()}).", email=False)


def create_article(db: Session, user: User, body: schemas.FAQIn, source_request_id: str | None = None) -> FAQArticle:
    a = FAQArticle(slug=body.slug or _slugify(body.title), title=body.title, body=body.body,
                   category_id=body.category_id, unit_id=_scope_unit(db, user, body.unit_id, body.category_id),
                   language=body.language, tags=body.tags, status="draft", version=1, author_id=user.id,
                   source_request_id=source_request_id)
    db.add(a)
    db.flush()
    _save_version(db, a, user)
    audit(db, user, "faq", a.id, "create", None, snapshot(a))
    if user.role == Role.AGENT:
        _notify_heads(db, a, user)
    return a


# ---------------- FAQ articles ----------------
@router.get("/admin/faq", response_model=schemas.FAQPage)
def list_faq(db: Session = Depends(get_db), _: User = Depends(require_staff),
             q: str | None = Query(None, max_length=200), category_id: int | None = None, unit_id: int | None = None,
             language: schemas.LangT | None = None, status: schemas.FAQStatusT | None = None,
             slug: str | None = Query(None, max_length=80),
             page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    query = db.query(FAQArticle)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(FAQArticle.title.ilike(like), FAQArticle.body.ilike(like), FAQArticle.slug.ilike(like)))
    for col, val in ((FAQArticle.category_id, category_id), (FAQArticle.unit_id, unit_id),
                     (FAQArticle.language, language), (FAQArticle.status, status), (FAQArticle.slug, slug)):
        if val is not None:
            query = query.filter(col == val)
    total = query.count()
    rows = (query.options(joinedload(FAQArticle.category), joinedload(FAQArticle.unit), joinedload(FAQArticle.author))
            .order_by(FAQArticle.updated_at.desc(), FAQArticle.id.desc())
            .offset((page - 1) * page_size).limit(page_size).all())
    return schemas.FAQPage(items=[_faq_out(a) for a in rows], total=total, page=page, page_size=page_size,
                           pages=max(1, math.ceil(total / page_size)))


@router.post("/admin/faq", response_model=schemas.FAQOut, status_code=201,
             summary="Create an FAQ article (always a draft; agents' drafts notify the unit head)")
def create_faq(body: schemas.FAQIn, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    a = create_article(db, user, body)
    db.commit()
    return _faq_out(a)


@router.get("/admin/faq/{article_id}", response_model=schemas.FAQOut)
def get_faq(article_id: int, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    return _faq_out(_get_faq(db, article_id))


@router.put("/admin/faq/{article_id}", response_model=schemas.FAQOut, summary="Edit; every content change is a new version")
def update_faq(article_id: int, body: schemas.FAQIn, db: Session = Depends(get_db),
               user: User = Depends(require_staff)):
    a = _get_faq(db, article_id)
    if not _can_edit(user, a):
        raise HTTPException(403, "Only an admin, the unit head or the draft's author can edit this article")
    old = snapshot(a)
    data = body.model_dump(exclude={"unit_id", "slug"})
    changed = any(getattr(a, k) != data[k] for k in VERSIONED)
    for k, v in data.items():
        setattr(a, k, v)
    if body.slug:
        a.slug = body.slug
    if user.role == Role.ADMIN and body.unit_id is not None:
        a.unit_id = _scope_unit(db, user, body.unit_id, a.category_id)
    if changed:
        a.version += 1
        a.updated_at = utcnow()
        db.flush()
        _save_version(db, a, user)
    audit(db, user, "faq", a.id, "update", old, snapshot(a))
    if a.status == "published":
        jobs.after_commit(db, embeddings.job_index_faq, a.id)
    db.commit()
    return _faq_out(a)


def _set_status(db: Session, user: User, a: FAQArticle, status: str) -> FAQArticle:
    if not can_publish(user, a.unit_id):
        raise HTTPException(403, "Only an admin or the unit head of this article's unit can publish or archive")
    old = snapshot(a)
    a.status = status
    if status == "published":
        a.approved_by, a.published_at = user.id, utcnow()
    audit(db, user, "faq", a.id, "publish" if status == "published" else "archive", old, snapshot(a))
    jobs.after_commit(db, embeddings.job_index_faq, a.id)
    db.commit()
    return a


@router.post("/admin/faq/{article_id}/publish", response_model=schemas.FAQOut)
def publish_faq(article_id: int, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    return _faq_out(_set_status(db, user, _get_faq(db, article_id), "published"))


@router.post("/admin/faq/{article_id}/archive", response_model=schemas.FAQOut)
def archive_faq(article_id: int, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    return _faq_out(_set_status(db, user, _get_faq(db, article_id), "archived"))


@router.get("/admin/faq/{article_id}/versions", response_model=list[schemas.FAQVersionOut])
def faq_versions(article_id: int, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    _get_faq(db, article_id)
    return (db.query(FAQArticleVersion).options(joinedload(FAQArticleVersion.editor))
            .filter_by(article_id=article_id).order_by(FAQArticleVersion.version.desc()).all())


@router.delete("/admin/faq/{article_id}", status_code=204)
def delete_faq(article_id: int, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    a = _get_faq(db, article_id)
    if not can_publish(user, a.unit_id) and not (a.status == "draft" and a.author_id == user.id):
        raise HTTPException(403, "Access denied")
    audit(db, user, "faq", a.id, "delete", snapshot(a), None)
    embeddings.remove(db, "faq", str(a.id))
    db.delete(a)
    db.commit()


@router.post("/faq/{article_id}/vote", summary="Helpful yes / no on a published article")
def vote(article_id: int, body: schemas.VoteIn, db: Session = Depends(get_db), _: User = Depends(current_user)):
    a = db.get(FAQArticle, article_id)
    if a is None or a.status != "published":
        raise HTTPException(404, "Article not found")
    if body.helpful:
        a.helpful_yes += 1
    else:
        a.helpful_no += 1
    db.commit()
    return {"helpful_yes": a.helpful_yes, "helpful_no": a.helpful_no}


# ---------------- reply templates ----------------
def _get_template(db: Session, template_id: int) -> ReplyTemplate:
    t = db.get(ReplyTemplate, template_id)
    if t is None:
        raise HTTPException(404, "Template not found")
    return t


def _can_edit_template(user: User, t: ReplyTemplate) -> bool:
    return can_publish(user, t.unit_id) or t.author_id == user.id


@router.get("/admin/reply-templates", response_model=list[schemas.TemplateOut])
def list_templates(db: Session = Depends(get_db), _: User = Depends(require_staff),
                   q: str | None = Query(None, max_length=200), category_id: int | None = None,
                   unit_id: int | None = None, language: schemas.LangT | None = None, active: bool | None = None):
    query = db.query(ReplyTemplate).options(joinedload(ReplyTemplate.category), joinedload(ReplyTemplate.unit))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(ReplyTemplate.title.ilike(like), ReplyTemplate.body.ilike(like)))
    for col, val in ((ReplyTemplate.category_id, category_id), (ReplyTemplate.unit_id, unit_id),
                     (ReplyTemplate.language, language), (ReplyTemplate.is_active, active)):
        if val is not None:
            query = query.filter(col == val)
    return [_template_out(t) for t in query.order_by(ReplyTemplate.usage_count.desc(), ReplyTemplate.id).limit(500)]


def create_template_row(db: Session, user: User, body: schemas.TemplateIn) -> ReplyTemplate:
    t = ReplyTemplate(**body.model_dump(exclude={"unit_id"}), unit_id=_scope_unit(db, user, body.unit_id, body.category_id),
                      author_id=user.id)
    db.add(t)
    db.flush()
    audit(db, user, "reply_template", t.id, "create", None, snapshot(t))
    jobs.after_commit(db, embeddings.job_index_template, t.id)
    return t


@router.post("/admin/reply-templates", response_model=schemas.TemplateOut, status_code=201)
def create_template(body: schemas.TemplateIn, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    t = create_template_row(db, user, body)
    db.commit()
    return _template_out(t)


@router.put("/admin/reply-templates/{template_id}", response_model=schemas.TemplateOut)
def update_template(template_id: int, body: schemas.TemplateIn, db: Session = Depends(get_db),
                    user: User = Depends(require_staff)):
    t = _get_template(db, template_id)
    if not _can_edit_template(user, t):
        raise HTTPException(403, "Only an admin, the unit head or the author can edit this template")
    old = snapshot(t)
    for k, v in body.model_dump(exclude={"unit_id"}).items():
        setattr(t, k, v)
    if user.role == Role.ADMIN and body.unit_id is not None:
        t.unit_id = _scope_unit(db, user, body.unit_id, t.category_id)
    audit(db, user, "reply_template", t.id, "update", old, snapshot(t))
    jobs.after_commit(db, embeddings.job_index_template, t.id)
    db.commit()
    return _template_out(t)


@router.delete("/admin/reply-templates/{template_id}", status_code=204)
def delete_template(template_id: int, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    t = _get_template(db, template_id)
    if not _can_edit_template(user, t):
        raise HTTPException(403, "Access denied")
    audit(db, user, "reply_template", t.id, "delete", snapshot(t), None)
    embeddings.remove(db, "template", str(t.id))
    db.delete(t)
    db.commit()


# ---------------- from a ticket ----------------
@router.post("/requests/{request_id}/propose-faq", response_model=schemas.FAQOut, status_code=201,
             summary="Agent proposes an FAQ (Draft) from a resolved request; the unit head is notified")
def propose_faq(request_id: str, body: schemas.ProposeFAQIn, db: Session = Depends(get_db),
                user: User = Depends(require_staff)):
    req = get_request_or_404(db, request_id, user)
    require_staff_access(user, req)
    if req.status not in (Status.RESOLVED, Status.CLOSED):
        raise HTTPException(409, {"message": "Only resolved requests can become FAQ articles"})
    reply = embeddings.final_public_reply(db, req)
    if not body.body and reply is None:
        raise HTTPException(422, "The request has no public answer to turn into an FAQ")
    names = embeddings.case_names(db, req)
    answer = body.body or "".join(f"<p>{html.escape(p)}</p>" for p in pii.mask(reply.body, names).split("\n") if p.strip())
    lang = body.language or embeddings.detect_language(reply.body if reply else req.description)
    data = schemas.FAQIn(title=body.title or pii.mask(req.subject, names), body=answer, category_id=req.category_id,
                         unit_id=req.unit_id, language=lang, tags=[])
    a = create_article(db, user, data, source_request_id=req.id)
    if user.role != Role.AGENT:
        _notify_heads(db, a, user)
    db.commit()
    return _faq_out(a)


@router.post("/requests/{request_id}/save-template", response_model=schemas.TemplateOut, status_code=201,
             summary="Save the last public agent reply of a request as a reply template")
def save_template(request_id: str, body: schemas.SaveTemplateIn, db: Session = Depends(get_db),
                  user: User = Depends(require_staff)):
    req = get_request_or_404(db, request_id, user)
    require_staff_access(user, req)
    text = body.body
    if not text:
        reply = embeddings.final_public_reply(db, req)
        if reply is None:
            raise HTTPException(422, "The request has no public reply to save")
        text = reply.body
        # Turn the concrete reply back into a reusable template.
        for value, ph in ((req.student.name, "{student_name}"), (req.id, "{request_id}"),
                          (req.unit.name if req.unit else "", "{unit}"), (reply.author.name, "{agent_name}")):
            if value:
                text = re.sub(re.escape(value), ph, text, flags=re.IGNORECASE)
        first = req.student.name.split()[0] if req.student and req.student.name else ""
        if len(first) >= 3:
            text = re.sub(rf"(?<!\w){re.escape(first)}(?!\w)", "{student_name}", text)
        text = pii.mask(text, [])
    lang = body.language or embeddings.detect_language(text)
    title = body.title or f"{req.category.name if req.category else 'Reply'}: {req.subject}"[:200]
    t = create_template_row(db, user, schemas.TemplateIn(title=title, body=text, category_id=req.category_id,
                                                         unit_id=req.unit_id, language=lang))
    db.commit()
    return _template_out(t)
