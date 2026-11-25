from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import EmailStr, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_prefix="QOLDAU_", extra="ignore",
                                      env_ignore_empty=True)

    app_name: str = "Qoldau - Student Request Routing & Support"
    environment: str = "development"
    # SQLite by default for local dev; docker-compose sets a PostgreSQL URL.
    database_url: str = f"sqlite:///{(BASE_DIR / 'qoldau.db').as_posix()}"
    secret_key: str = "change-me-in-production-please-32-bytes-min"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    upload_dir: Path = BASE_DIR / "uploads"
    max_upload_mb: int = 10
    signed_url_seconds: int = 900
    attachment_mode: Literal["auto", "disabled", "development", "clamav"] = "auto"
    clamav_host: str = ""
    clamav_port: int = Field(default=3310, ge=1, le=65535)

    demo_login_enabled: bool = False
    pilot_directory_published: bool = False
    pilot_support_email: EmailStr | None = None
    pilot_data_contact: EmailStr | None = None
    pilot_privacy_url: str = ""

    model_dir: Path = BASE_DIR / "app" / "ml" / "artifacts"
    confidence_threshold: float = 0.60

    # An agent counts as "online" if seen within this window (or has an open WebSocket).
    online_window_minutes: int = 15
    scheduler_enabled: bool = True
    sla_job_seconds: int = 60
    auto_close_days: int = 7

    # Without a configured relay no delivery is attempted.
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_security: Literal["starttls", "ssl"] = "starttls"
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: EmailStr | None = None
    email_portal_url: str = ""
    email_job_seconds: int = Field(default=20, ge=1)
    email_max_attempts: int = Field(default=6, ge=1, le=20)

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

    # Sprint 5. Counters are stored in the application database and shared by API workers.
    rate_limits_enabled: bool = True
    rate_limit_login_ip_per_minute: int = 60
    rate_limit_login_account_per_minute: int = 10
    rate_limit_refresh_per_minute: int = 60
    rate_limit_write_per_hour: int = 120
    rate_limit_message_per_minute: int = 60
    rate_limit_ai_per_minute: int = 60
    rate_limit_export_per_hour: int = 10
    rate_limit_retrain_per_hour: int = 2
    # Only these peers may supply X-Forwarded-For. Leave empty without a trusted reverse proxy.
    trusted_proxy_cidrs: list[str] = []

    @property
    def effective_attachment_mode(self) -> str:
        if self.attachment_mode != "auto":
            return self.attachment_mode
        return "development" if self.environment == "development" else "disabled"

    @model_validator(mode="after")
    def validate_production(self):
        if self.environment not in ("development", "production"):
            raise ValueError("QOLDAU_ENVIRONMENT must be development or production")
        if self.environment == "production":
            if self.secret_key == "change-me-in-production-please-32-bytes-min" or len(self.secret_key) < 32:
                raise ValueError("Production requires a unique QOLDAU_SECRET_KEY of at least 32 characters")
            if not self.database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Production requires a PostgreSQL QOLDAU_DATABASE_URL")
            if not self.cors_origins or any(not origin.startswith("https://") for origin in self.cors_origins):
                raise ValueError("Production QOLDAU_CORS_ORIGINS must contain HTTPS origins only")
            if self.demo_login_enabled or self.attachment_mode == "development":
                raise ValueError("Production cannot enable development login or attachment checks")
        if self.attachment_mode == "clamav" and not self.clamav_host.strip():
            raise ValueError("ClamAV mode requires QOLDAU_CLAMAV_HOST")
        if bool(self.smtp_user) != bool(self.smtp_password):
            raise ValueError("Configure both SMTP username and password for authenticated delivery")
        if self.smtp_host and (not self.email_portal_url or not self.smtp_from):
            raise ValueError("SMTP requires QOLDAU_EMAIL_PORTAL_URL and QOLDAU_SMTP_FROM")
        for name, value in (("email portal", self.email_portal_url), ("privacy link", self.pilot_privacy_url)):
            if value:
                url = urlsplit(value)
                local_dev_portal = (name == "email portal" and self.environment == "development"
                                    and url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"})
                if (url.scheme != "https" and not local_dev_portal) or not url.hostname or url.username or url.password:
                    raise ValueError("The email portal and public privacy links must use absolute HTTPS URLs; "
                                     "development email portals may use HTTP on loopback only")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
