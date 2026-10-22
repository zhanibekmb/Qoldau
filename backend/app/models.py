from datetime import datetime

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, LargeBinary, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, utcnow


class Role:
    STUDENT = "student"
    AGENT = "agent"
    UNIT_HEAD = "unit_head"
    ADMIN = "admin"
    ALL = (STUDENT, AGENT, UNIT_HEAD, ADMIN)
    STAFF = (AGENT, UNIT_HEAD, ADMIN)


class Status:
    SUBMITTED = "Submitted"
    CLASSIFIED = "Classified"
    ROUTED = "Routed"
    IN_PROGRESS = "In Progress"
    WAITING = "Waiting for Student"
    RESOLVED = "Resolved"
    CLOSED = "Closed"
    NEEDS_REVIEW = "Needs Review"
    REOPENED = "Reopened"
    ALL = (SUBMITTED, CLASSIFIED, ROUTED, IN_PROGRESS, WAITING, RESOLVED, CLOSED, NEEDS_REVIEW, REOPENED)
    OPEN = (SUBMITTED, CLASSIFIED, ROUTED, IN_PROGRESS, WAITING, NEEDS_REVIEW, REOPENED)


class Priority:
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    ORDER = (LOW, MEDIUM, HIGH, CRITICAL)


class Unit(Base):
    __tablename__ = "units"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    email: Mapped[str] = mapped_column(String(160), default="")
    head_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", use_alter=True, ondelete="SET NULL"))
    working_hours: Mapped[str] = mapped_column(String(60), default="Mon-Fri 09:00-18:00")
    is_triage: Mapped[bool] = mapped_column(Boolean, default=False)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default=Role.STUDENT, index=True)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id", ondelete="SET NULL"), index=True)
    language: Mapped[str] = mapped_column(String(2), default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_assigned_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    unit: Mapped[Unit | None] = relationship(foreign_keys=[unit_id])


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id", ondelete="SET NULL"))
    default_workflow: Mapped[str] = mapped_column(String(20), default="standard")
    base_priority_weight: Mapped[int] = mapped_column(Integer, default=15)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    unit: Mapped[Unit | None] = relationship()


class RoutingRule(Base):
    __tablename__ = "routing_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), index=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    category: Mapped[Category] = relationship()
    unit: Mapped[Unit] = relationship()


class SLAPolicy(Base):
    __tablename__ = "sla_policies"
    id: Mapped[int] = mapped_column(primary_key=True)
    priority: Mapped[str] = mapped_column(String(10), unique=True)
    first_response_hours: Mapped[float] = mapped_column(Float)
    resolution_hours: Mapped[float] = mapped_column(Float)
    use_working_hours: Mapped[bool] = mapped_column(Boolean, default=False)


class UrgencyKeyword(Base):
    __tablename__ = "urgency_keywords"
    id: Mapped[int] = mapped_column(primary_key=True)
    keyword: Mapped[str] = mapped_column(String(80), unique=True)
    weight: Mapped[int] = mapped_column(Integer, default=10)
    # Critical keywords (health / safety / harassment) force priority Critical regardless of score.
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    language: Mapped[str] = mapped_column(String(2), default="en")


class Request(Base):
    __tablename__ = "requests"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # REQ-YYYY-#####
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text)
    student_category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    ai_category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    ai_confidence: Mapped[float | None] = mapped_column(Float)
    ai_alternatives: Mapped[list | None] = mapped_column(JSON)
    ai_keywords: Mapped[list | None] = mapped_column(JSON)
    ai_priority: Mapped[str | None] = mapped_column(String(10))
    model_version: Mapped[str | None] = mapped_column(String(40))
    priority: Mapped[str] = mapped_column(String(10), default=Priority.MEDIUM, index=True)
    priority_score: Mapped[int] = mapped_column(Integer, default=40)
    priority_reasons: Mapped[list | None] = mapped_column(JSON)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id", ondelete="SET NULL"), index=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(24), default=Status.SUBMITTED, index=True)
    workflow: Mapped[str] = mapped_column(String(20), default="standard")
    workflow_step: Mapped[int] = mapped_column(Integer, default=0)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)

    sla_first_response_due: Mapped[datetime | None] = mapped_column(DateTime)
    sla_resolution_due: Mapped[datetime | None] = mapped_column(DateTime)
    sla_paused_at: Mapped[datetime | None] = mapped_column(DateTime)
    sla_warned: Mapped[bool] = mapped_column(Boolean, default=False)
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False)
    # FAQ / similar-case suggestions the student saw while writing the request (US20).
    suggestions_shown: Mapped[list | None] = mapped_column(JSON)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    student: Mapped[User] = relationship(foreign_keys=[student_id])
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id])
    category: Mapped[Category | None] = relationship(foreign_keys=[category_id])
    ai_category: Mapped[Category | None] = relationship(foreign_keys=[ai_category_id])
    unit: Mapped[Unit | None] = relationship(foreign_keys=[unit_id])
    csat: Mapped["CSAT | None"] = relationship(back_populates="request", uselist=False)


class StatusHistory(Base):
    __tablename__ = "status_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(24))
    to_status: Mapped[str] = mapped_column(String(24))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reason: Mapped[str] = mapped_column(String(20), default="manual")  # rule / AI / manual / system
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    actor: Mapped[User | None] = relationship()


class RoutingLog(Base):
    __tablename__ = "routing_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    from_unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id", ondelete="SET NULL"))
    to_unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id", ondelete="SET NULL"))
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reason: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(10), default="rule")  # rule / AI / manual
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    to_unit: Mapped[Unit | None] = relationship(foreign_keys=[to_unit_id])
    assignee: Mapped[User | None] = relationship(foreign_keys=[assignee_id])


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text, default="")
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    author: Mapped[User] = relationship()
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="message")


class Attachment(Base):
    __tablename__ = "attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"))
    uploader_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(200))
    content_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(200))
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    message: Mapped[Message | None] = relationship(back_populates="attachments")


class AIFeedback(Base):
    __tablename__ = "ai_feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    predicted_category: Mapped[str | None] = mapped_column(String(80))
    corrected_category: Mapped[str | None] = mapped_column(String(80))
    predicted_priority: Mapped[str | None] = mapped_column(String(10))
    corrected_priority: Mapped[str | None] = mapped_column(String(10))
    predicted_unit: Mapped[str | None] = mapped_column(String(120))
    corrected_unit: Mapped[str | None] = mapped_column(String(120))
    agent_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[str | None] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class EmailOutbox(Base):
    __tablename__ = "email_outbox"
    id: Mapped[int] = mapped_column(primary_key=True)
    to: Mapped[str] = mapped_column(String(160))
    subject: Mapped[str] = mapped_column(String(250))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="queued")  # queued / sent / failed / logged
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CSAT(Base):
    __tablename__ = "csat"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), unique=True)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    request: Mapped[Request] = relationship(back_populates="csat")


class Escalation(Base):
    __tablename__ = "escalations"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # sla_warning / sla_breach / low_csat / critical
    target: Mapped[str] = mapped_column(String(20))  # first_response / resolution / -
    notified_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    entity: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[str] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(10))  # create / update / delete
    old: Mapped[dict | None] = mapped_column(JSON)
    new: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    actor: Mapped[User | None] = relationship()


class ModelRegistry(Base):
    __tablename__ = "model_registry"
    __table_args__ = (UniqueConstraint("model_type", "version", name="uq_model_registry_type_version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(40))
    model_type: Mapped[str] = mapped_column(String(20), default="classifier")  # classifier / priority
    algorithm: Mapped[str] = mapped_column(String(80))
    accuracy: Mapped[float] = mapped_column(Float)
    macro_f1: Mapped[float] = mapped_column(Float)
    # accuracy, macro_f1, per_class_f1, confusion_matrix {labels, matrix}, test_size, ...
    metrics: Mapped[dict | None] = mapped_column(JSON)
    train_size: Mapped[int] = mapped_column(Integer, default=0)
    feedback_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(12), default="active")  # active / candidate / archived
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    artifact_path: Mapped[str | None] = mapped_column(String(300))
    training_run_id: Mapped[int | None] = mapped_column(ForeignKey("training_runs.id", ondelete="SET NULL"))
    activated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime)
    trained_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---------------- Sprint 4 (US17-US21) ----------------
class TrainingRun(Base):
    __tablename__ = "training_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(10), default="queued")  # queued / running / done / failed
    trigger: Mapped[str] = mapped_column(String(10), default="manual")  # manual / schedule
    force: Mapped[bool] = mapped_column(Boolean, default=False)
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    feedback_count: Mapped[int] = mapped_column(Integer, default=0)
    logs: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[dict | None] = mapped_column(JSON)  # {classifier: {version, promoted}, priority: {...}}
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class ReportJob(Base):
    __tablename__ = "report_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(8))  # excel / pdf
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(10), default="queued")  # queued / running / done / failed
    file_key: Mapped[str | None] = mapped_column(String(200))
    file_size: Mapped[int | None] = mapped_column(Integer)
    row_count: Mapped[int | None] = mapped_column(Integer)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    unit_scope: Mapped[int | None] = mapped_column(ForeignKey("units.id", ondelete="SET NULL"))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)


class FAQArticle(Base):
    __tablename__ = "faq_articles"
    id: Mapped[int] = mapped_column(primary_key=True)
    # Translations of the same article share a slug ("ordering-transcript" in kz / ru / en).
    slug: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)  # sanitised HTML
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id", ondelete="SET NULL"), index=True)
    language: Mapped[str] = mapped_column(String(2), default="en")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(10), default="draft", index=True)  # draft / published / archived
    version: Mapped[int] = mapped_column(Integer, default=1)
    views: Mapped[int] = mapped_column(Integer, default=0)
    helpful_yes: Mapped[int] = mapped_column(Integer, default=0)
    helpful_no: Mapped[int] = mapped_column(Integer, default=0)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    source_request_id: Mapped[str | None] = mapped_column(ForeignKey("requests.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)

    category: Mapped[Category | None] = relationship()
    unit: Mapped[Unit | None] = relationship()
    author: Mapped[User | None] = relationship(foreign_keys=[author_id])


class FAQArticleVersion(Base):
    __tablename__ = "faq_article_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("faq_articles.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    category_id: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[str] = mapped_column(String(2))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(10))
    editor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    editor: Mapped[User | None] = relationship()


class ReplyTemplate(Base):
    __tablename__ = "reply_templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    # Plain text with placeholders {student_name} {request_id} {unit} {agent_name}.
    body: Mapped[str] = mapped_column(Text)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id", ondelete="SET NULL"), index=True)
    language: Mapped[str] = mapped_column(String(2), default="en")
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    category: Mapped[Category | None] = relationship()
    unit: Mapped[Unit | None] = relationship()


class ContentEmbedding(Base):
    """Vector index rows. Stored as packed float32 so SQLite and PostgreSQL share one schema;
    ml/embeddings.py is the single place to switch the similarity search to pgvector."""
    __tablename__ = "content_embeddings"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", name="uq_embedding_entity"),
                      Index("ix_embedding_lookup", "entity_type", "language"))
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(10))  # faq / request / template
    entity_id: Mapped[str] = mapped_column(String(20))
    language: Mapped[str] = mapped_column(String(2))
    category_id: Mapped[int | None] = mapped_column(Integer)
    unit_id: Mapped[int | None] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(80))
    dim: Mapped[int] = mapped_column(Integer)
    vector: Mapped[bytes] = mapped_column(LargeBinary)
    text_hash: Mapped[str] = mapped_column(String(40))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class SuggestionEvent(Base):
    __tablename__ = "suggestion_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str | None] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str | None] = mapped_column(String(40), index=True)
    type: Mapped[str] = mapped_column(String(12))  # faq / similar / smart_reply
    item_id: Mapped[str] = mapped_column(String(40))  # faq:12, request:REQ-2026-00001, template:3
    action: Mapped[str] = mapped_column(String(10))  # shown / opened / used / edited / ignored / deflected
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    unit_id: Mapped[int | None] = mapped_column(Integer, index=True)
    category_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
