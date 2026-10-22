"""Background jobs (exports, retraining, re-indexing).

A small in-process thread pool stands in for Celery: jobs are queued on the DB session and only
start after the transaction commits (like realtime pushes), so a job never reads uncommitted or
rolled-back rows. Each job opens its own session. With settings.jobs_inline the job runs
synchronously right after commit, which keeps tests deterministic.
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from sqlalchemy import event
from sqlalchemy.orm import Session

from ..config import get_settings

log = logging.getLogger(__name__)
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="qoldau-job")


def _run(fn: Callable, args: tuple) -> None:
    try:
        fn(*args)
    except Exception:
        log.exception("background job %s failed", getattr(fn, "__name__", fn))


def submit(fn: Callable, *args) -> None:
    """Run now (inline mode) or on the pool. Use after_commit() when the job reads rows you just wrote."""
    if get_settings().jobs_inline:
        _run(fn, args)
    else:
        _pool.submit(_run, fn, args)


def after_commit(db: Session, fn: Callable, *args) -> None:
    db.info.setdefault("jobs", []).append((fn, args))


@event.listens_for(Session, "after_commit")
def _start_jobs(session: Session) -> None:
    for fn, args in session.info.pop("jobs", []):
        submit(fn, *args)


@event.listens_for(Session, "after_rollback")
def _drop_jobs(session: Session) -> None:
    session.info.pop("jobs", None)
