from fastapi import APIRouter, Depends, HTTPException, Request

from ..config import ANALYTICS_ADMIN_EMAIL
from .auth_routes import _require_same_origin, current_identity

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/visit")
def record_visit(request: Request):
    _require_same_origin(request)
    request.app.state.history.record_metric("visit")
    return {"recorded": True}


@router.get("/summary")
def summary(
    request: Request,
    identity=Depends(current_identity),
):
    email = request.app.state.auth.email_for_user(identity.user_id)
    if not email or email.casefold() != ANALYTICS_ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Analytics access is restricted.")
    return request.app.state.history.analytics_summary()
