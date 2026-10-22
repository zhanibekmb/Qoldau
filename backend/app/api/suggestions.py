"""FAQ / similar-request suggestions (US20), smart replies (US19) and suggestion usage events."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db
from ..models import User
from ..security import current_user, require_staff
from ..services import suggestions
from .common import get_request_or_404, require_staff_access

router = APIRouter(tags=["suggestions"])


@router.post("/ai/similar", response_model=schemas.SimilarOut,
             summary="Text -> up to 3 Published FAQ articles + up to 3 anonymised similar resolved cases (US20)")
def similar(body: schemas.SimilarIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return suggestions.similar(db, user, body.text, body.language, body.category_id)


@router.get("/ai/suggestions/{request_id}", response_model=schemas.SmartReplyOut,
            summary="Top-3 smart reply suggestions for a ticket (US19); never auto-sent")
def smart_replies(request_id: str, db: Session = Depends(get_db), user: User = Depends(require_staff)):
    req = get_request_or_404(db, request_id, user)
    require_staff_access(user, req)
    out = suggestions.smart_replies(db, req, user)
    db.commit()  # "shown" events
    return out


@router.post("/suggestions/events", summary="Log shown / opened / used / edited / ignored / deflected")
def events(body: schemas.SuggestionEventIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    req = get_request_or_404(db, body.request_id, user) if body.request_id else None
    try:
        n = suggestions.record(db, user, body, req)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    db.commit()
    return {"recorded": n}
