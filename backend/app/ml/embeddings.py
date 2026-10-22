"""Multilingual text embeddings and similarity search (US19 / US20 / US21).

Providers sit behind one small interface (encode -> L2-normalised float32 rows):

- "local" (default, no downloads): hashed character n-grams catch wording and KZ/RU morphology,
  and the active classifier's category probabilities add a language-independent topic signal, so a
  Kazakh query still lands near the Russian / English article about the same thing.
- "sentence-transformers": any SentenceTransformer model, intfloat/multilingual-e5-small by default
  (QOLDAU_EMBEDDING_PROVIDER / QOLDAU_EMBEDDING_MODEL). Needs `pip install sentence-transformers`.

Vectors live in content_embeddings (packed float32, portable across SQLite and PostgreSQL) and are
searched in memory with numpy, which is fast for tens of thousands of rows. search() is the one
place to switch to a pgvector HNSW query when the index outgrows memory.

Usage:  python -m app.ml.embeddings --reindex     (re-embed all published FAQ, templates, resolved requests)
"""
from __future__ import annotations

import argparse
import hashlib
import html
import logging
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import SessionLocal, utcnow
from ..models import ContentEmbedding, FAQArticle, Message, ReplyTemplate, Request, Role, Status, User
from . import pii
from .classifier import get_classifier

log = logging.getLogger(__name__)

KZ_LETTERS = set("әғқңөұүһі")
_CYR = re.compile(r"[а-яё]", re.IGNORECASE)
_TAGS = re.compile(r"<[^>]+>")
_PLACEHOLDER = re.compile(r"\{(student_name|request_id|unit|agent_name)\}")
AUTO_INDEX = True  # the seed script turns per-request indexing off and re-indexes once at the end


def detect_language(text: str) -> str:
    low = (text or "").lower()
    if any(ch in KZ_LETTERS for ch in low):
        return "kz"
    if len(_CYR.findall(low)) >= 2:
        return "ru"
    return "en"


def plain_text(body: str) -> str:
    """HTML (FAQ bodies) -> readable plain text."""
    text = re.sub(r"</(p|li|h\d|blockquote)>|<br\s*/?>", "\n", body or "", flags=re.IGNORECASE)
    return re.sub(r"[ \t]+", " ", html.unescape(_TAGS.sub("", text))).strip()


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", plain_text(text).lower().replace("ё", "е"))


class EmbeddingProvider:
    name: str
    dim: int

    def encode(self, texts: list[str], kind: str = "passage") -> np.ndarray:  # pragma: no cover - interface
        raise NotImplementedError


class LocalProvider(EmbeddingProvider):
    name = "local-v1"
    HASH_DIM = 1024
    TOPIC_WEIGHT = 0.35  # cosine = 0.65 * lexical + 0.35 * topic

    def __init__(self) -> None:
        self.vec = HashingVectorizer(analyzer="char_wb", ngram_range=(3, 5), n_features=self.HASH_DIM,
                                     alternate_sign=False, norm="l2", preprocessor=_normalise)
        self.n_topics = len(get_classifier().classes)
        self.dim = self.HASH_DIM + self.n_topics

    def encode(self, texts: list[str], kind: str = "passage") -> np.ndarray:
        lex = self.vec.transform(texts).toarray().astype(np.float32)
        clf = get_classifier()
        x = clf.pipeline.named_steps["features"].transform([plain_text(t) for t in texts])
        topic = clf.pipeline.named_steps["clf"].predict_proba(x).astype(np.float32)
        if topic.shape[1] != self.n_topics:  # a retrained model with a different label set
            topic = np.resize(topic, (topic.shape[0], self.n_topics))
        topic /= np.linalg.norm(topic, axis=1, keepdims=True) + 1e-9
        out = np.hstack([lex * np.sqrt(1 - self.TOPIC_WEIGHT), topic * np.sqrt(self.TOPIC_WEIGHT)])
        return out / (np.linalg.norm(out, axis=1, keepdims=True) + 1e-9)


class SentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer  # optional dependency
        self.model = SentenceTransformer(model_name)
        self.name = f"st:{model_name}"[:80]
        self.dim = int(self.model.get_sentence_embedding_dimension())
        self.e5 = "e5" in model_name.lower()

    def encode(self, texts: list[str], kind: str = "passage") -> np.ndarray:
        prefix = (f"{kind}: " if self.e5 else "")
        vecs = self.model.encode([prefix + plain_text(t) for t in texts], normalize_embeddings=True, batch_size=32)
        return np.asarray(vecs, dtype=np.float32)


@lru_cache
def get_provider() -> EmbeddingProvider:
    s = get_settings()
    if s.embedding_provider == "sentence-transformers":
        return SentenceTransformerProvider(s.embedding_model)
    return LocalProvider()


# Query vectors are cached (stand-in for a Redis cache); typing produces many repeated queries.
_qcache: OrderedDict[tuple[str, str], np.ndarray] = OrderedDict()
_qlock = threading.Lock()


def encode_query(text: str) -> np.ndarray:
    p = get_provider()
    key = (p.name, _normalise(text)[:500])
    with _qlock:
        if key in _qcache:
            _qcache.move_to_end(key)
            return _qcache[key]
    vec = p.encode([text], kind="query")[0]
    with _qlock:
        _qcache[key] = vec
        while len(_qcache) > 512:
            _qcache.popitem(last=False)
    return vec


# ---------------- index ----------------
@dataclass
class Hit:
    entity_id: str
    score: float
    language: str
    category_id: int | None
    unit_id: int | None


class _Matrix:
    """In-memory copy of one entity type's vectors; rebuilt when this process writes or after a TTL."""
    TTL = 60.0

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.stale: set[str] = set()
        self.data: dict[str, tuple[float, list, np.ndarray]] = {}

    def invalidate(self, entity_type: str) -> None:
        with self.lock:
            self.stale.add(entity_type)

    def get(self, db: Session, entity_type: str, provider: str):
        with self.lock:
            cached = self.data.get(entity_type)
            if cached and entity_type not in self.stale and time.monotonic() - cached[0] < self.TTL:
                return cached[1], cached[2]
        rows = (db.query(ContentEmbedding.entity_id, ContentEmbedding.language, ContentEmbedding.category_id,
                         ContentEmbedding.unit_id, ContentEmbedding.vector, ContentEmbedding.dim)
                .filter(ContentEmbedding.entity_type == entity_type, ContentEmbedding.provider == provider).all())
        meta = [(r.entity_id, r.language, r.category_id, r.unit_id) for r in rows]
        mat = (np.vstack([np.frombuffer(r.vector, dtype=np.float32, count=r.dim) for r in rows])
               if rows else np.zeros((0, 1), dtype=np.float32))
        with self.lock:
            self.data[entity_type] = (time.monotonic(), meta, mat)
            self.stale.discard(entity_type)
        return meta, mat


_matrix = _Matrix()


def upsert(db: Session, entity_type: str, entity_id: str, text: str, language: str,
           category_id: int | None = None, unit_id: int | None = None) -> ContentEmbedding:
    p = get_provider()
    digest = hashlib.sha1(f"{p.name}|{language}|{category_id}|{unit_id}|{text}".encode()).hexdigest()
    row = db.query(ContentEmbedding).filter_by(entity_type=entity_type, entity_id=str(entity_id)).first()
    if row and row.text_hash == digest and row.provider == p.name:
        return row
    vec = p.encode([text])[0].astype(np.float32)
    if row is None:
        row = ContentEmbedding(entity_type=entity_type, entity_id=str(entity_id))
        db.add(row)
    row.language, row.category_id, row.unit_id = language, category_id, unit_id
    row.provider, row.dim, row.vector, row.text_hash, row.updated_at = p.name, len(vec), vec.tobytes(), digest, utcnow()
    _matrix.invalidate(entity_type)
    return row


def remove(db: Session, entity_type: str, entity_id: str) -> None:
    db.query(ContentEmbedding).filter_by(entity_type=entity_type, entity_id=str(entity_id)).delete()
    _matrix.invalidate(entity_type)


def search(db: Session, query: str, entity_type: str, top_k: int = 5, language: str | None = None,
           category_id: int | None = None, unit_id: int | None = None, exclude: set[str] | None = None,
           min_score: float = 0.0) -> list[Hit]:
    meta, mat = _matrix.get(db, entity_type, get_provider().name)
    if not meta:
        return []
    q = encode_query(query)
    if mat.shape[1] != q.shape[0]:
        return []
    scores = mat @ q
    hits: list[Hit] = []
    for i in np.argsort(-scores):
        eid, lang, cat, unit = meta[i]
        s = float(scores[i])
        if s < min_score:
            break
        if (language and lang != language) or (category_id and cat != category_id) or (unit_id and unit != unit_id):
            continue
        if exclude and eid in exclude:
            continue
        hits.append(Hit(eid, round(s, 4), lang, cat, unit))
        if len(hits) >= top_k:
            break
    return hits


# ---------------- what gets indexed ----------------
def faq_text(a: FAQArticle) -> str:
    return f"{a.title}\n{a.title}\n{' '.join(a.tags or [])}\n{plain_text(a.body)}"


def template_text(t: ReplyTemplate) -> str:
    return f"{t.title}\n{_PLACEHOLDER.sub(' ', t.body)}"


def final_public_reply(db: Session, req: Request) -> Message | None:
    """Last non-internal staff message: the answer that resolved the request."""
    return (db.query(Message).join(User, User.id == Message.author_id)
            .filter(Message.request_id == req.id, Message.is_internal.is_(False), User.role.in_(Role.STAFF),
                    Message.body != "")
            .order_by(Message.id.desc()).first())


def case_names(db: Session, req: Request) -> list[str]:
    """People whose names must never leave this request (the student and the staff on it)."""
    names = [req.student.name] if req.student else []
    names += [n for (n,) in db.query(User.name).join(Message, Message.author_id == User.id)
              .filter(Message.request_id == req.id).distinct()]
    return names


def request_text(db: Session, req: Request) -> str:
    reply = final_public_reply(db, req)
    names = case_names(db, req)
    return pii.mask(f"{req.subject}\n{req.description}\n{reply.body if reply else ''}", names)


def index_faq(db: Session, a: FAQArticle) -> None:
    if a.status == "published":
        upsert(db, "faq", str(a.id), faq_text(a), a.language, a.category_id, a.unit_id)
    else:
        remove(db, "faq", str(a.id))


def index_template(db: Session, t: ReplyTemplate) -> None:
    if t.is_active:
        upsert(db, "template", str(t.id), template_text(t), t.language, t.category_id, t.unit_id)
    else:
        remove(db, "template", str(t.id))


def index_request(db: Session, req: Request) -> None:
    if req.status in (Status.RESOLVED, Status.CLOSED):
        lang = detect_language(f"{req.subject} {req.description}")
        upsert(db, "request", req.id, request_text(db, req), lang, req.category_id, req.unit_id)


def reindex_all(db: Session) -> dict:
    counts = {"faq": 0, "template": 0, "request": 0}
    for a in db.query(FAQArticle):
        index_faq(db, a)
        counts["faq"] += a.status == "published"
    for t in db.query(ReplyTemplate):
        index_template(db, t)
        counts["template"] += t.is_active
    for r in db.query(Request).filter(Request.status.in_((Status.RESOLVED, Status.CLOSED))):
        index_request(db, r)
        counts["request"] += 1
    # Drop rows of a previous provider so searches never mix vector spaces.
    db.query(ContentEmbedding).filter(ContentEmbedding.provider != get_provider().name).delete()
    for et in counts:
        _matrix.invalidate(et)
    return counts


# ---------------- background jobs (run via services.jobs) ----------------
def _with_session(fn):
    def run(*args):
        db = SessionLocal()
        try:
            fn(db, *args)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    run.__name__ = fn.__name__
    return run


@_with_session
def job_index_faq(db: Session, article_id: int) -> None:
    a = db.get(FAQArticle, article_id)
    if a is None:
        remove(db, "faq", str(article_id))
    else:
        index_faq(db, a)


@_with_session
def job_index_template(db: Session, template_id: int) -> None:
    t = db.get(ReplyTemplate, template_id)
    if t is None:
        remove(db, "template", str(template_id))
    else:
        index_template(db, t)


@_with_session
def job_index_request(db: Session, request_id: str) -> None:
    req = db.get(Request, request_id)
    if req is not None:
        index_request(db, req)


@_with_session
def job_reindex_all(db: Session) -> None:
    log.info("re-indexed embeddings: %s", reindex_all(db))


@_with_session
def job_ensure_index(db: Session) -> None:
    """Startup: index anything published/resolved that has no vector for the current provider yet."""
    have = {(t, i) for t, i in db.query(ContentEmbedding.entity_type, ContentEmbedding.entity_id)
            .filter(ContentEmbedding.provider == get_provider().name)}
    n = 0
    for a in db.query(FAQArticle).filter_by(status="published"):
        if ("faq", str(a.id)) not in have:
            index_faq(db, a)
            n += 1
    for t in db.query(ReplyTemplate).filter_by(is_active=True):
        if ("template", str(t.id)) not in have:
            index_template(db, t)
            n += 1
    for r in db.query(Request).filter(Request.status.in_((Status.RESOLVED, Status.CLOSED))):
        if ("request", r.id) not in have:
            index_request(db, r)
            n += 1
    if n:
        log.info("indexed %d new items", n)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reindex", action="store_true", help="re-embed everything (e.g. after changing provider)")
    args = ap.parse_args()
    db = SessionLocal()
    try:
        counts = reindex_all(db) if args.reindex else None
        if counts is None:
            job_ensure_index()
            counts = {t: db.query(ContentEmbedding).filter_by(entity_type=t).count() for t in ("faq", "template", "request")}
        db.commit()
        print(f"Embeddings ({get_provider().name}): {counts}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
