from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_prefix="QOLDAU_", extra="ignore")

    app_name: str = "Qoldau - Student Request Routing & Support"
    # SQLite by default for local dev; docker-compose sets a PostgreSQL URL.
    database_url: str = f"sqlite:///{(BASE_DIR / 'qoldau.db').as_posix()}"
    secret_key: str = "change-me-in-production-please-32-bytes-min"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    upload_dir: Path = BASE_DIR / "uploads"
    max_upload_mb: int = 10
    signed_url_seconds: int = 900

    model_dir: Path = BASE_DIR / "app" / "ml" / "artifacts"
    confidence_threshold: float = 0.60

    # An agent counts as "online" if seen within this window (or has an open WebSocket).
    online_window_minutes: int = 15
    scheduler_enabled: bool = True
    sla_job_seconds: int = 60
    auto_close_days: int = 7

    # Email: when smtp_host is empty, emails are only written to the email_outbox table.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@qoldau.edu.kz"

    # Sprint 4. Background jobs run on an in-process thread pool (stand-in for Celery);
    # jobs_inline runs them synchronously after commit (tests, single-shot scripts).
    jobs_inline: bool = False
    # Exports are stored privately on disk (stand-in for S3) and downloaded through signed links.
    export_dir: Path = BASE_DIR / "exports"
    export_link_hours: int = 24
    # "local" = built-in multilingual char-n-gram + category embedding (no downloads);
    # "sentence-transformers" = embedding_model via the sentence-transformers package.
    embedding_provider: str = "local"
    embedding_model: str = "intfloat/multilingual-e5-small"
    retrain_min_feedback: int = 200
    retrain_weekly: bool = True
    model_sync_seconds: int = 30  # workers pick up an activated / rolled back model within this window
    smart_reply_llm_enabled: bool = False  # optional LLM rewriter for smart replies (provider interface only)
    smart_reply_llm_provider: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
