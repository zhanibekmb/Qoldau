"""Report export (US17): background jobs producing .xlsx / .pdf with signed 24 h download links.

Admin = all units; Unit Head = own unit only (enforced in the query); Student / Agent = HTTP 403.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db
from ..models import Category, ReportJob, Role, Status, Unit, User
from ..security import require_head_or_admin, sign_export, verify_export_signature
from ..services import jobs, reports
from .admin import audit

router = APIRouter(prefix="/export", tags=["export"])

MEDIA = {"excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "pdf": "application/pdf"}


def job_out(job: ReportJob, viewer: User) -> schemas.ReportJobOut:
    out = schemas.ReportJobOut.model_validate(job)
    if job.status == "done" and job.file_key:
        exp, sig = sign_export(job.id, viewer.id)
        out.download_url = f"/api/v1/export/files/{job.id}?uid={viewer.id}&exp={exp}&sig={sig}"
    return out


def _create(kind: str, body: schemas.ExportIn, db: Session, user: User) -> schemas.ReportJobOut:
    if body.unit_id is not None and db.get(Unit, body.unit_id) is None:
        raise HTTPException(422, "Unknown unit")
    if body.category_id is not None and db.get(Category, body.category_id) is None:
        raise HTTPException(422, "Unknown category")
    if body.status is not None and body.status not in Status.ALL:
        raise HTTPException(422, "Unknown status")
    filters = body.model_dump(mode="json", exclude_none=True)
    if user.role != Role.ADMIN:
        if user.unit_id is None:
            raise HTTPException(403, "Access denied")
        filters["unit_id"] = user.unit_id
    job = ReportJob(type=kind, filters=filters, status="queued", requested_by=user.id,
                    unit_scope=filters.get("unit_id"))
    db.add(job)
    db.flush()
    audit(db, user, "export", job.id, "create", None, {"type": kind, **filters})
    jobs.after_commit(db, reports.run_export, job.id)
    db.commit()
    db.refresh(job)
    return job_out(job, user)


@router.post("/excel", response_model=schemas.ReportJobOut, status_code=202,
             summary="Excel report (Summary, By Category, By Unit, SLA, AI Accuracy, Raw Requests)")
def export_excel(body: schemas.ExportIn, db: Session = Depends(get_db), user: User = Depends(require_head_or_admin)):
    return _create("excel", body, db, user)


@router.post("/pdf", response_model=schemas.ReportJobOut, status_code=202,
             summary="Branded PDF report with KPIs and charts")
def export_pdf(body: schemas.ExportIn, db: Session = Depends(get_db), user: User = Depends(require_head_or_admin)):
    return _create("pdf", body, db, user)


@router.get("/jobs", response_model=list[schemas.ReportJobOut], summary="My export jobs")
def my_jobs(db: Session = Depends(get_db), user: User = Depends(require_head_or_admin),
            limit: int = Query(50, le=200)):
    rows = (db.query(ReportJob).filter_by(requested_by=user.id).order_by(ReportJob.id.desc()).limit(limit).all())
    return [job_out(j, user) for j in rows]


@router.get("/jobs/{job_id}", response_model=schemas.ReportJobOut)
def get_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(require_head_or_admin)):
    job = db.get(ReportJob, job_id)
    if job is None or (job.requested_by != user.id and user.role != Role.ADMIN):
        raise HTTPException(404, "Export not found")
    return job_out(job, user)


@router.get("/files/{job_id}", summary="Download via signed link (valid 24 h)")
def download(job_id: int, uid: int, exp: int, sig: str, db: Session = Depends(get_db)):
    if not verify_export_signature(job_id, uid, exp, sig):
        raise HTTPException(403, "Link expired or invalid")
    job = db.get(ReportJob, job_id)
    viewer = db.get(User, uid)
    if job is None or viewer is None or not viewer.is_active or job.status != "done":
        raise HTTPException(404, "Not found")
    if job.requested_by != viewer.id and viewer.role != Role.ADMIN:
        raise HTTPException(404, "Not found")
    path = reports.file_path(job)
    if not path.exists():
        raise HTTPException(404, "File missing")
    ext = "xlsx" if job.type == "excel" else "pdf"
    return FileResponse(path, media_type=MEDIA[job.type], filename=f"qoldau-report-{job.id}.{ext}")
