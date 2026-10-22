"""Self-service suggestions for students (US20) and smart replies for agents (US19).

Both are retrieval only (embeddings + templates), so they work without an external LLM. Text from
other students' requests is always PII-masked, and internal notes are never read (only the final
public staff reply of a resolved request is reused).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
import threading
import time

from sqlalchemy.orm import Session

from .. import schemas
from ..config import get_settings
from ..ml import embeddings, pii
from ..models import FAQArticle, Message, ReplyTemplate, Request, Role, Status, SuggestionEvent, User

log = logging.getLogger(__name__)

FAQ_MIN_SCORE = 0.35
CASE_MIN_SCORE = 0.40
RELATIVE_CUTOFF = 0.8  # also drop anything far below the best match: three good answers beat one good and two noisy
REPLY_MIN_SCORE = 0.25
CATEGORY_BOOST = 0.20  # a curated template for the request's own category beats a near-identical past reply
KB_PENALTY = 0.05  # an answer distilled from an article is less specific than a written reply
SNIPPET = 220

KB_REPLY = {
    "en": "Hello {student_name},\n\n{answer}\n\nMore details: “{title}” in our FAQ.\n\nBest regards,\n{agent_name}, {unit}",
    "ru": "Здравствуйте, {student_name}!\n\n{answer}\n\nПодробнее: «{title}» в разделе FAQ.\n\nС уважением,\n{agent_name}, {unit}",
    "kz": "Сәлеметсіз бе, {student_name}!\n\n{answer}\n\nТолығырақ: FAQ бөліміндегі «{title}».\n\nҚұрметпен,\n{agent_name}, {unit}",
}


def _snippet(text: str, n: int = SNIPPET) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def _sentences(text: str, k: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip())
    return " ".join(parts[:k])


# ---------------- US20: student suggestions while typing ----------------
def _faq_items(db: Session, hits: list[embeddings.Hit], seen_slugs: set[str], limit: int) -> list[schemas.SuggestionItem]:
    items = []
    arts = {str(a.id): a for a in db.query(FAQArticle).filter(FAQArticle.id.in_([int(h.entity_id) for h in hits]))}
    for h in hits:
        a = arts.get(h.entity_id)
        # Only Published articles ever reach students, whatever the index says.
        if a is None or a.status != "published" or a.slug in seen_slugs:
            continue
        seen_slugs.add(a.slug)
        items.append(schemas.SuggestionItem(
            id=f"faq:{a.id}", source="faq", title=a.title, snippet=_snippet(embeddings.plain_text(a.body)),
            body=a.body, score=h.score, language=a.language, category=a.category.name if a.category else None,
            unit=a.unit.name if a.unit else None))
        if len(items) >= limit:
            break
    return items


def case_token(request_id: str) -> str:
    """Opaque id for a similar case: students must not learn other students' request IDs."""
    digest = hmac.new(get_settings().secret_key.encode(), request_id.encode(), hashlib.sha256).hexdigest()
    return f"case:{digest[:16]}"


def _close_to_best(hits: list[embeddings.Hit]) -> list[embeddings.Hit]:
    return [h for h in hits if h.score >= hits[0].score * RELATIVE_CUTOFF] if hits else hits


def similar(db: Session, user: User, text: str, language: str | None = None,
            category_id: int | None = None) -> schemas.SimilarOut:
    lang = language or embeddings.detect_language(text)
    seen: set[str] = set()
    faq = _faq_items(db, _close_to_best(embeddings.search(db, text, "faq", top_k=8, language=lang,
                                                          category_id=category_id, min_score=FAQ_MIN_SCORE)), seen, 3)
    if not faq:  # nothing in the student's language: fall back to the best match in another language
        faq = _faq_items(db, _close_to_best(embeddings.search(db, text, "faq", top_k=8, category_id=category_id,
                                                              min_score=FAQ_MIN_SCORE + 0.1)), seen, 3)

    cases: list[schemas.SuggestionItem] = []
    titles: set[str] = set()
    hits = _close_to_best(embeddings.search(db, text, "request", top_k=12, language=lang, min_score=CASE_MIN_SCORE))
    reqs = {r.id: r for r in db.query(Request).filter(Request.id.in_([h.entity_id for h in hits]))}
    for h in hits:
        r = reqs.get(h.entity_id)
        if r is None or r.student_id == user.id or r.status not in (Status.RESOLVED, Status.CLOSED):
            continue
        reply = embeddings.final_public_reply(db, r)
        if reply is None:
            continue
        names = embeddings.case_names(db, r)
        # Anonymised: no request ID, no names, no contact data - only the problem and how it was solved.
        title = _snippet(pii.mask(r.subject, names), 120)
        if title.lower() in titles:
            continue
        titles.add(title.lower())
        cases.append(schemas.SuggestionItem(
            id=case_token(r.id), source="similar_case", title=title,
            snippet=_snippet(pii.mask(reply.body, names)), score=h.score, language=h.language,
            category=r.category.name if r.category else None, unit=r.unit.name if r.unit else None))
        if len(cases) >= 3:
            break
    return schemas.SimilarOut(language=lang, faq=faq, cases=cases)


# ---------------- US19: smart replies for agents ----------------
class ReplyRewriter:
    """Optional LLM polish of a suggestion (SMART_REPLY_LLM_ENABLED). No provider ships by default:
    register one with register_rewriter() and it must never add facts or personal data."""
    name = "none"

    def rewrite(self, text: str, language: str) -> str:  # pragma: no cover - interface
        return text


_REWRITERS: dict[str, ReplyRewriter] = {}


def register_rewriter(key: str, rewriter: ReplyRewriter) -> None:
    _REWRITERS[key] = rewriter


def get_rewriter() -> ReplyRewriter | None:
    s = get_settings()
    if not s.smart_reply_llm_enabled:
        return None
    rw = _REWRITERS.get(s.smart_reply_llm_provider)
    if rw is None:
        log.warning("SMART_REPLY_LLM_ENABLED but provider %r is not registered", s.smart_reply_llm_provider)
    return rw


_cache: dict[tuple[str, int], tuple[float, schemas.SmartReplyOut]] = {}
_cache_lock = threading.Lock()
CACHE_SECONDS = 300


def invalidate(request_id: str) -> None:
    with _cache_lock:
        for key in [k for k in _cache if k[0] == request_id]:
            _cache.pop(key, None)


def fill(text: str, req: Request, agent: User) -> str:
    values = {"{student_name}": req.student.name if req.student else "", "{request_id}": req.id,
              "{unit}": req.unit.name if req.unit else "", "{agent_name}": agent.name}
    for ph, v in values.items():
        text = text.replace(ph, v)
    return text


def _case_reply(db: Session, case: Request, reply: Message) -> str:
    """Another student's resolved case -> reusable reply: their name becomes a placeholder, all other PII is masked."""
    text = reply.body
    for name, ph in ((case.student.name if case.student else "", "{student_name}"), (reply.author.name, "{agent_name}")):
        for part in sorted({name, *name.split()}, key=len, reverse=True):
            if len(part) >= 3:
                text = re.sub(rf"(?<!\w){re.escape(part)}(?!\w)", ph, text, flags=re.IGNORECASE)
        text = re.sub(r"(\{(?:student|agent)_name\})(\s+\1)+", r"\1", text)
    return pii.mask(text, embeddings.case_names(db, case))


def _query_text(db: Session, req: Request) -> str:
    last = (db.query(Message.body).filter(Message.request_id == req.id, Message.is_internal.is_(False),
                                         Message.author_id == req.student_id)
            .order_by(Message.id.desc()).first())
    return f"{req.subject}\n{req.description}\n{last[0] if last else ''}"


def smart_replies(db: Session, req: Request, agent: User) -> schemas.SmartReplyOut:
    key = (req.id, agent.id)
    with _cache_lock:
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
            return hit[1]

    lang = embeddings.detect_language(f"{req.subject} {req.description}")
    query = _query_text(db, req)
    cands: list[schemas.SmartReply] = []

    t_hits = embeddings.search(db, query, "template", top_k=6, language=lang, min_score=REPLY_MIN_SCORE)
    temps = {str(t.id): t for t in db.query(ReplyTemplate).filter(ReplyTemplate.id.in_([int(h.entity_id) for h in t_hits]))}
    for h in t_hits:
        t = temps.get(h.entity_id)
        if t is None or not t.is_active:
            continue
        boost = CATEGORY_BOOST if t.category_id and t.category_id == req.category_id else 0.0
        cands.append(schemas.SmartReply(text=t.body, source="template", source_id=f"template:{t.id}", title=t.title,
                                        score=round(h.score + boost, 4), language=t.language))

    c_hits = embeddings.search(db, query, "request", top_k=8, language=lang, exclude={req.id},
                               min_score=REPLY_MIN_SCORE)
    cases = {r.id: r for r in db.query(Request).filter(Request.id.in_([h.entity_id for h in c_hits]))}
    for h in c_hits:
        case = cases.get(h.entity_id)
        if case is None or case.status not in (Status.RESOLVED, Status.CLOSED):
            continue
        reply = embeddings.final_public_reply(db, case)  # never internal notes
        if reply is None or embeddings.detect_language(reply.body) != lang:
            continue
        cands.append(schemas.SmartReply(text=_case_reply(db, case, reply), source="similar_case",
                                        source_id=f"request:{case.id}", title=_snippet(pii.mask(case.subject, []), 80),
                                        score=h.score, language=lang))

    k_hits = embeddings.search(db, query, "faq", top_k=4, language=lang, min_score=REPLY_MIN_SCORE)
    arts = {str(a.id): a for a in db.query(FAQArticle).filter(FAQArticle.id.in_([int(h.entity_id) for h in k_hits]))}
    for h in k_hits:
        a = arts.get(h.entity_id)
        if a is None or a.status != "published":
            continue
        text = KB_REPLY.get(lang, KB_REPLY["en"]).format(student_name="{student_name}", agent_name="{agent_name}",
                                                         unit="{unit}", title=a.title,
                                                         answer=_sentences(embeddings.plain_text(a.body), 3))
        cands.append(schemas.SmartReply(text=text, source="kb", source_id=f"faq:{a.id}", title=a.title,
                                        score=round(h.score - KB_PENALTY, 4), language=a.language))

    cands.sort(key=lambda c: -c.score)
    out, seen = [], set()
    for c in cands:
        norm = re.sub(r"\W+", "", c.text.lower())[:200]
        if norm in seen:
            continue
        seen.add(norm)
        out.append(c.model_copy(update={"text": fill(c.text, req, agent)}))
        if len(out) >= 3:
            break

    rewriter = get_rewriter()
    if rewriter:
        out = [c.model_copy(update={"text": rewriter.rewrite(c.text, lang)}) for c in out]
    result = schemas.SmartReplyOut(request_id=req.id, language=lang, suggestions=out,
                                   rewriter=rewriter.name if rewriter else None)
    _log_shown(db, req, agent, out)
    with _cache_lock:
        _cache[key] = (time.monotonic(), result)
    return result


def _log_shown(db: Session, req: Request, agent: User, items: list[schemas.SmartReply]) -> None:
    logged = {i for (i,) in db.query(SuggestionEvent.item_id).filter_by(request_id=req.id, type="smart_reply",
                                                                        action="shown", user_id=agent.id)}
    for c in items:
        if c.source_id not in logged:
            db.add(SuggestionEvent(request_id=req.id, type="smart_reply", item_id=c.source_id, action="shown",
                                   user_id=agent.id, unit_id=req.unit_id, category_id=req.category_id))


# ---------------- usage events ----------------
def record(db: Session, user: User, body: schemas.SuggestionEventIn, req: Request | None) -> int:
    if body.type == "smart_reply" and user.role not in Role.STAFF:
        raise PermissionError("smart replies are staff-only")
    if body.action == "deflected" and user.role != Role.STUDENT:
        raise PermissionError("only students deflect")
    n = 0
    for item in body.item_ids:
        kind, _, ref = item.partition(":")
        unit_id = req.unit_id if req else None
        category_id = req.category_id if req else None
        if kind == "faq" and ref.isdigit():
            a = db.get(FAQArticle, int(ref))
            if a is None:
                continue
            unit_id, category_id = unit_id or a.unit_id, category_id or a.category_id
            if body.action == "opened":
                a.views += 1
        elif kind == "template" and ref.isdigit() and body.action in ("used", "edited"):
            t = db.get(ReplyTemplate, int(ref))
            if t is not None:
                t.usage_count += 1
        db.add(SuggestionEvent(request_id=req.id if req else None, session_id=body.session_id, type=body.type,
                               item_id=item[:40], action=body.action, user_id=user.id, unit_id=unit_id,
                               category_id=category_id))
        n += 1
    return n


def attach_session(db: Session, req: Request, student: User, session_id: str) -> None:
    """When the student submits after all, keep the suggestions they saw with the request."""
    events = (db.query(SuggestionEvent)
              .filter(SuggestionEvent.session_id == session_id, SuggestionEvent.user_id == student.id,
                      SuggestionEvent.request_id.is_(None)).all())
    for e in events:
        e.request_id = req.id
    shown = sorted({e.item_id for e in events if e.action == "shown"})
    req.suggestions_shown = shown or None
