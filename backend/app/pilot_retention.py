"""Inspect or erase one closed request or completed export after approved retention review."""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import SessionLocal, utcnow
from .models import AuditLog, ContentEmbedding, FAQArticle, ReportJob, Request, Status, SuggestionEvent

REQUEST_ID = re.compile(r"REQ-[0-9]{4}-[0-9]{5,13}")
ATTACHMENT_NAME = re.compile(r"[0-9a-f]{32}\.(pdf|jpg|jpeg|png|docx)")


def _storage_path(root: Path, key: str) -> Path:
    root = root.resolve()
    path = root / key
    if path == root or not path.is_relative_to(root) or path.resolve() != path:
        raise ValueError("Storage path is outside the configured directory or is a link")
    return path


def _request_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    files = sorted(directory.iterdir())
    if any(file.is_symlink() or not file.is_file() or not ATTACHMENT_NAME.fullmatch(file.name) for file in files):
        raise ValueError("Unexpected contents in the attachment directory. Inspect it before erasing.")
    return files


def purge_request(db: Session, request_id: str, before: datetime, apply: bool = False) -> dict:
    if not REQUEST_ID.fullmatch(request_id):
        raise ValueError("Invalid request ID")
    directory = _storage_path(get_settings().upload_dir, request_id)
    files = _request_files(directory)
    req = db.scalar(select(Request).where(Request.id == request_id).with_for_update())
    if req and (req.status != Status.CLOSED or not req.closed_at or req.closed_at >= before):
        raise ValueError("Request is open or has not reached the approved cutoff")
    faq_ids = list(db.scalars(select(FAQArticle.id).where(FAQArticle.source_request_id == request_id)))
    plan = {"request_id": request_id, "request_found": req is not None, "attachment_files": len(files),
            "faq_to_review": faq_ids, "applied": apply}
    if not apply:
        return plan
    if faq_ids:
        raise ValueError(f"Review and resolve linked FAQ data before erasing this request: {faq_ids}")
    if req:
        removed = db.execute(delete(Request).where(Request.id == request_id, Request.status == Status.CLOSED,
                                                   Request.closed_at < before))
        if removed.rowcount != 1:
            raise ValueError("Request changed. Run the inspection again.")
    db.execute(delete(ContentEmbedding).where(ContentEmbedding.entity_type == "request",
                                               ContentEmbedding.entity_id == request_id))
    db.execute(delete(SuggestionEvent).where(SuggestionEvent.item_id == f"request:{request_id}"))
    db.execute(delete(AuditLog).where(AuditLog.entity == "request", AuditLog.entity_id == request_id))
    db.commit()
    # The directory is deterministic, so a rerun removes files left by an interrupted cleanup.
    for file in _request_files(directory):
        file.unlink(missing_ok=True)
    if directory.exists():
        directory.rmdir()
    return plan


def purge_report(db: Session, job_id: int, before: datetime, apply: bool = False) -> dict:
    job = db.scalar(select(ReportJob).where(ReportJob.id == job_id).with_for_update())
    if job and (job.status not in ("done", "failed") or not job.finished_at or job.finished_at >= before):
        raise ValueError("Export is still running or has not reached the approved cutoff")
    path = _storage_path(get_settings().export_dir, job.file_key) if job and job.file_key else None
    plan = {"report_id": job_id, "report_found": job is not None, "file_found": bool(path and path.is_file()),
            "applied": apply}
    if apply and job:
        if path:
            path.unlink(missing_ok=True)
        db.delete(job)
        db.commit()
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--request")
    target.add_argument("--report", type=int)
    parser.add_argument("--before", required=True, type=datetime.fromisoformat, help="Approved UTC cutoff YYYY-MM-DD")
    parser.add_argument("--apply", action="store_true", help="Actually erase records and files")
    args = parser.parse_args()
    if args.before.tzinfo or args.before > utcnow():
        parser.error("Use a past UTC cutoff without a time zone suffix")
    with SessionLocal() as db:
        try:
            result = (purge_request(db, args.request, args.before, args.apply) if args.request else
                      purge_report(db, args.report, args.before, args.apply))
        except (ValueError, OSError) as exc:
            parser.exit(1, f"{exc}\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
