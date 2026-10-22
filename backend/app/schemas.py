import html
import re
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer, field_validator

UTCDateTime = Annotated[datetime, PlainSerializer(lambda d: d.isoformat() + "Z" if d.tzinfo is None else d.isoformat(),
                                                  return_type=str)]
PriorityT = Literal["Critical", "High", "Medium", "Low"]
RoleT = Literal["student", "agent", "unit_head", "admin"]
LangT = Literal["en", "ru", "kz"]

_TAG = re.compile(r"<[^>]*>")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize(text: str) -> str:
    """Strip HTML tags and control characters; the frontend also escapes on render."""
    return html.unescape(_CTRL.sub("", _TAG.sub("", text or ""))).strip()


RICH_TAGS = ["p", "br", "strong", "b", "em", "i", "u", "ul", "ol", "li", "a", "h3", "h4", "blockquote", "code"]


def sanitize_html(text: str) -> str:
    """Allow-list rich text for FAQ bodies (US21): no scripts, styles, event handlers or js: links."""
    import bleach
    cleaned = bleach.clean(_CTRL.sub("", text or ""), tags=RICH_TAGS, attributes={"a": ["href", "title"]},
                           protocols=["http", "https", "mailto"], strip=True, strip_comments=True)
    return bleach.linkify(cleaned, callbacks=[_link_attrs]).strip()


def _link_attrs(attrs, new=False):
    attrs[(None, "rel")] = "noopener noreferrer"
    attrs[(None, "target")] = "_blank"
    return attrs


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth ----
class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(ORM):
    id: int
    name: str
    email: str
    role: RoleT
    unit_id: int | None
    unit_name: str | None = None
    language: LangT
    is_active: bool


class UserBrief(ORM):
    id: int
    name: str


# ---- requests ----
DESCRIPTION_MAX = 2000
SUBJECT_MAX = 150


class RequestCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=SUBJECT_MAX)
    description: str = Field(min_length=10, max_length=DESCRIPTION_MAX)
    category_id: int | None = None  # student's own guess; None = "Not sure"
    # Suggestion session of the New Request form; the suggestions shown are saved with the request (US20).
    suggestion_session: str | None = Field(default=None, max_length=40)

    @field_validator("subject", "description")
    @classmethod
    def _clean(cls, v: str) -> str:
        v = sanitize(v)
        if not v:
            raise ValueError("must not be empty")
        return v


class CategoryBrief(ORM):
    id: int
    name: str


class UnitBrief(ORM):
    id: int
    name: str


class SLAState(BaseModel):
    target: str
    due_at: UTCDateTime
    remaining_seconds: int
    remaining_fraction: float
    color: str
    paused: bool
    breached: bool


class RequestCard(BaseModel):
    id: str
    subject: str
    status: str
    priority: PriorityT
    priority_score: int
    category: CategoryBrief | None
    unit: UnitBrief | None
    assignee: UserBrief | None
    student: UserBrief | None = None
    ai_confidence: float | None
    escalated: bool
    sla: SLAState | None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class AIDecision(BaseModel):
    predicted_category: CategoryBrief | None
    confidence: float | None
    alternatives: list[dict]
    keywords: list[str]
    predicted_priority: str | None
    priority_reasons: list[str]
    predicted_unit: UnitBrief | None
    student_category: CategoryBrief | None
    model_version: str | None


class CSATOut(ORM):
    rating: int
    comment: str
    created_at: UTCDateTime


class RequestDetail(RequestCard):
    description: str
    workflow: str
    workflow_steps: list[str]
    workflow_step: int
    first_response_at: UTCDateTime | None
    resolved_at: UTCDateTime | None
    csat: CSATOut | None
    allowed_transitions: list[str] = []
    ai: AIDecision | None = None  # staff only


class Page(BaseModel):
    items: list[RequestCard]
    total: int
    page: int
    page_size: int
    pages: int


class StatusPatch(BaseModel):
    status: str
    message: str | None = Field(default=None, max_length=DESCRIPTION_MAX)


class AssignIn(BaseModel):
    assignee_id: int


class OverrideIn(BaseModel):
    category_id: int | None = None
    priority: PriorityT | None = None
    unit_id: int | None = None
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def _clean(cls, v: str) -> str:
        return sanitize(v)


class TimelineEvent(BaseModel):
    id: str
    kind: str  # submitted / status / ai / routing / message / note / escalation / step / csat
    title: str
    detail: str | None = None
    status: str | None = None
    actor: str | None = None
    internal: bool = False
    created_at: UTCDateTime


# ---- AI ----
class ClassifyIn(BaseModel):
    subject: str = ""
    description: str = Field(min_length=0, max_length=DESCRIPTION_MAX)


class ClassifyOut(BaseModel):
    category: str
    category_id: int | None
    confidence: float
    needs_review: bool
    alternatives: list[dict]
    keywords: list[str]
    model_version: str


class PriorityOut(BaseModel):
    priority: PriorityT
    score: int
    critical: bool
    reasons: list[str]


# ---- messaging ----
class AttachmentOut(BaseModel):
    id: int
    filename: str
    content_type: str
    size: int
    url: str


class MessageIn(BaseModel):
    body: str = Field(default="", max_length=DESCRIPTION_MAX)
    is_internal: bool = False
    attachment_ids: list[int] = []

    @field_validator("body")
    @classmethod
    def _clean(cls, v: str) -> str:
        return sanitize(v)


class MessageOut(BaseModel):
    id: int
    request_id: str
    author: UserBrief
    author_role: str
    body: str
    is_internal: bool
    read_at: UTCDateTime | None
    created_at: UTCDateTime
    attachments: list[AttachmentOut]


class CSATIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)

    @field_validator("comment")
    @classmethod
    def _clean(cls, v: str) -> str:
        return sanitize(v)


class NotificationOut(ORM):
    id: int
    type: str
    title: str
    body: str
    request_id: str | None
    is_read: bool
    created_at: UTCDateTime


# ---- admin ----
class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    unit_id: int | None = None
    default_workflow: Literal["standard", "approval", "document", "urgent", "triage"] = "standard"
    base_priority_weight: int = Field(default=15, ge=0, le=60)
    is_active: bool = True


class CategoryOut(CategoryIn, ORM):
    id: int


class UnitIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = ""
    head_user_id: int | None = None
    working_hours: str = "Mon-Fri 09:00-18:00"
    is_triage: bool = False


class UnitOut(UnitIn, ORM):
    id: int


class RoutingRuleIn(BaseModel):
    category_id: int
    unit_id: int
    is_active: bool = True


class RoutingRuleOut(RoutingRuleIn, ORM):
    id: int
    category_name: str | None = None
    unit_name: str | None = None
    created_at: UTCDateTime


class SLAPolicyIn(BaseModel):
    priority: PriorityT
    first_response_hours: float = Field(gt=0, le=720)
    resolution_hours: float = Field(gt=0, le=2160)
    use_working_hours: bool = False


class SLAPolicyOut(SLAPolicyIn, ORM):
    id: int


class KeywordIn(BaseModel):
    keyword: str = Field(min_length=2, max_length=80)
    weight: int = Field(ge=-30, le=60)
    is_critical: bool = False
    language: LangT = "en"


class KeywordOut(KeywordIn, ORM):
    id: int


class UserIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    role: RoleT
    unit_id: int | None = None
    language: LangT = "en"
    is_active: bool = True
    password: str | None = Field(default=None, min_length=6, max_length=200)


class AuditOut(ORM):
    id: int
    actor: UserBrief | None
    entity: str
    entity_id: str
    action: str
    old: dict | None
    new: dict | None
    created_at: UTCDateTime


# ---- Sprint 4: knowledge base (US21) ----
FAQStatusT = Literal["draft", "published", "archived"]
PLACEHOLDERS = ("{student_name}", "{request_id}", "{unit}", "{agent_name}")


class FAQIn(BaseModel):
    slug: str | None = Field(default=None, max_length=80, description="Shared by translations; derived from title")
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10, max_length=20000, description="Rich text (HTML); sanitised server-side")
    category_id: int | None = None
    unit_id: int | None = None
    language: LangT = "en"
    tags: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("title")
    @classmethod
    def _clean_title(cls, v: str) -> str:
        return sanitize(v)

    @field_validator("body")
    @classmethod
    def _clean_body(cls, v: str) -> str:
        return sanitize_html(v)

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, v: list[str]) -> list[str]:
        return [t for t in (sanitize(x)[:40] for x in v) if t]

    @field_validator("slug")
    @classmethod
    def _clean_slug(cls, v: str | None) -> str | None:
        return re.sub(r"[^a-z0-9-]+", "-", v.lower()).strip("-")[:80] or None if v else None


class FAQOut(ORM):
    id: int
    slug: str
    title: str
    body: str
    category_id: int | None
    category_name: str | None = None
    unit_id: int | None
    unit_name: str | None = None
    language: LangT
    tags: list[str]
    status: FAQStatusT
    version: int
    views: int
    helpful_yes: int
    helpful_no: int
    helpful_pct: float | None = None
    author: UserBrief | None = None
    approved_by: int | None
    source_request_id: str | None
    created_at: UTCDateTime
    updated_at: UTCDateTime
    published_at: UTCDateTime | None


class FAQPage(BaseModel):
    items: list[FAQOut]
    total: int
    page: int
    page_size: int
    pages: int


class FAQVersionOut(ORM):
    id: int
    version: int
    title: str
    body: str
    category_id: int | None
    language: str
    tags: list[str]
    status: str
    editor: UserBrief | None
    created_at: UTCDateTime


class VoteIn(BaseModel):
    helpful: bool


class TemplateIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=5, max_length=DESCRIPTION_MAX)
    category_id: int | None = None
    unit_id: int | None = None
    language: LangT = "en"
    is_active: bool = True

    @field_validator("title", "body")
    @classmethod
    def _clean(cls, v: str) -> str:
        return sanitize(v)


class TemplateOut(ORM):
    id: int
    title: str
    body: str
    category_id: int | None
    category_name: str | None = None
    unit_id: int | None
    unit_name: str | None = None
    language: LangT
    usage_count: int
    is_active: bool
    author_id: int | None
    created_at: UTCDateTime
    updated_at: UTCDateTime


class ProposeFAQIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, max_length=20000)
    language: LangT | None = None


class SaveTemplateIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, max_length=DESCRIPTION_MAX)
    language: LangT | None = None


# ---- Sprint 4: suggestions (US19 / US20) ----
class SimilarIn(BaseModel):
    text: str = Field(min_length=1, max_length=DESCRIPTION_MAX)
    language: LangT | None = None
    category_id: int | None = None


class SuggestionItem(BaseModel):
    id: str  # "faq:12" / "case:<opaque token>"
    source: Literal["faq", "similar_case"]
    title: str
    snippet: str
    body: str | None = None  # full FAQ answer (sanitised HTML) for inline reading
    score: float
    language: str
    category: str | None = None
    unit: str | None = None


class SimilarOut(BaseModel):
    language: str
    faq: list[SuggestionItem]
    cases: list[SuggestionItem]


class SmartReply(BaseModel):
    text: str
    source: Literal["template", "similar_case", "kb"]
    source_id: str
    title: str
    score: float
    language: str


class SmartReplyOut(BaseModel):
    request_id: str
    language: str
    suggestions: list[SmartReply]
    rewriter: str | None = None


class SuggestionEventIn(BaseModel):
    session_id: str | None = Field(default=None, max_length=40)
    request_id: str | None = Field(default=None, max_length=20)
    type: Literal["faq", "similar", "smart_reply"]
    item_ids: list[str] = Field(min_length=1, max_length=10)
    action: Literal["shown", "opened", "used", "edited", "ignored", "deflected"]


# ---- Sprint 4: AI retraining & model management (US18) ----
class RetrainIn(BaseModel):
    force: bool = False


class TrainingRunOut(ORM):
    id: int
    status: str
    trigger: str
    force: bool
    feedback_count: int
    logs: str
    result: dict | None
    error: str | None
    created_at: UTCDateTime
    started_at: UTCDateTime | None
    finished_at: UTCDateTime | None


class ModelOut(ORM):
    id: int
    version: str
    model_type: str
    algorithm: str
    accuracy: float
    macro_f1: float
    train_size: int
    feedback_count: int
    status: str
    is_active: bool
    trained_at: UTCDateTime
    activated_at: UTCDateTime | None
    metrics: dict | None = None


# ---- Sprint 4: report export (US17) ----
class ExportIn(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    days: int | None = Field(default=None, ge=1, le=3650)
    unit_id: int | None = None
    category_id: int | None = None
    priority: PriorityT | None = None
    status: str | None = Field(default=None, max_length=24)


class ReportJobOut(ORM):
    id: int
    type: str
    filters: dict
    status: str
    row_count: int | None
    file_size: int | None
    error: str | None
    created_at: UTCDateTime
    finished_at: UTCDateTime | None
    download_url: str | None = None
