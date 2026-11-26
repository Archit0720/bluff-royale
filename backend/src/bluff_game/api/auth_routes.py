from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from ..auth import AuthenticationError
from ..config import (
    ALLOWED_ORIGINS,
    APP_ENV,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SAMESITE,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


class GoogleCredential(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credential: str = Field(min_length=1, max_length=10000)
    nonce: str = Field(min_length=1, max_length=256)


def _require_same_origin(request: Request):
    if request.headers.get("origin") not in ALLOWED_ORIGINS:
        raise HTTPException(status_code=403, detail="Request origin is not allowed.")


def current_identity(request: Request):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        _require_same_origin(request)
    identity = request.app.state.auth.identity_for_token(
        request.cookies.get(SESSION_COOKIE_NAME)
    )
    if identity is None:
        raise HTTPException(status_code=401, detail="Sign-in is required.")
    return identity


@router.get("/nonce")
def nonce(request: Request):
    return {"nonce": request.app.state.auth.create_nonce()}


@router.post("/google")
def google_login(
    body: GoogleCredential,
    request: Request,
    response: Response,
):
    _require_same_origin(request)
    if APP_ENV == "production" and request.url.scheme != "https":
        raise HTTPException(
            status_code=400,
            detail="Google credentials must be submitted over HTTPS.",
        )
    try:
        token, _ = request.app.state.auth.login(body.credential, body.nonce)
    except AuthenticationError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=request.app.state.auth.session_ttl_seconds,
        httponly=True,
        secure=APP_ENV == "production",
        samesite=SESSION_COOKIE_SAMESITE,
        path="/",
    )
    return {"authenticated": True}


@router.get("/me")
def me(request: Request, identity=Depends(current_identity)):
    profile = request.app.state.auth.profile(identity.user_id)
    if profile is None:
        raise HTTPException(status_code=401, detail="App session is no longer valid.")
    return {"authenticated": True, **profile}


@router.get("/me/matches")
def my_matches(
    request: Request,
    identity=Depends(current_identity),
):
    return request.app.state.history.by_user(identity.user_id)


@router.post("/logout")
def logout(request: Request, response: Response):
    _require_same_origin(request)
    request.app.state.auth.revoke(request.cookies.get(SESSION_COOKIE_NAME))
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        secure=APP_ENV == "production",
        httponly=True,
        samesite=SESSION_COOKIE_SAMESITE,
        path="/",
    )
    return {"authenticated": False}
