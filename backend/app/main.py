import asyncio
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import admin, ai, analytics, auth, export, kb, messages, meta, requests, suggestions, ws
from .config import get_settings
from .db import SessionLocal
from .ml import embeddings, training
from .ml.classifier import load_or_train
from .services import jobs, sla
from .services.realtime import hub

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("qoldau")
logging.getLogger("apscheduler").setLevel(logging.WARNING)


def sla_job() -> None:
    db = SessionLocal()
    try:
        result = sla.run_tick(db)
        if any(result.values()):
            log.info("SLA tick: %s", result)
    except Exception:
        db.rollback()
        log.exception("SLA tick failed")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    hub.bind_loop(asyncio.get_running_loop())
    load_or_train()  # warm the model so the first classification is fast
    training.sync_active_model_job()  # serve the version marked active in model_registry (US18)
    jobs.submit(embeddings.job_ensure_index)  # embed anything published/resolved that has no vector yet
    scheduler = None
    if settings.scheduler_enabled:
        scheduler = BackgroundScheduler(timezone="UTC")
        scheduler.add_job(sla_job, "interval", seconds=settings.sla_job_seconds, id="sla", max_instances=1,
                          coalesce=True)
        # Other workers activate / roll back models by polling the registry (no downtime, < 1 min).
        scheduler.add_job(training.sync_active_model_job, "interval", seconds=settings.model_sync_seconds,
                          id="model_sync", max_instances=1, coalesce=True)
        if settings.retrain_weekly:
            scheduler.add_job(training.scheduled_retrain, "cron", day_of_week="mon", hour=2, id="retrain",
                              max_instances=1, coalesce=True)
        scheduler.start()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="1.4.0", lifespan=lifespan,
                  description="AI Student Request Routing & Support System - Sprints 1-4 (US1-US21).",
                  docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])
    for r in (auth, requests, ai, suggestions, messages, analytics, export, admin, kb, meta):
        app.include_router(r.router, prefix="/api/v1")
    app.include_router(ws.router)

    @app.get("/api/health", tags=["meta"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
