import logging
import smtplib
import time
from collections import deque
from email.message import EmailMessage
from threading import Lock

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.concurrency import run_in_threadpool

from ..config import (
    FEEDBACK_TO_EMAIL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
)
from .auth_routes import _require_same_origin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["feedback"])
_feedback_lock = Lock()
_feedback_sent_at: deque[float] = deque()


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=10, max_length=3000)

    @field_validator("message")
    @classmethod
    def require_nonblank_message(cls, value: str):
        value = value.strip()
        if len(value) < 10:
            raise ValueError("Feedback must contain at least 10 non-space characters.")
        return value


def _send_feedback(message: str):
    email = EmailMessage()
    email["From"] = SMTP_USERNAME or FEEDBACK_TO_EMAIL
    email["To"] = FEEDBACK_TO_EMAIL
    email["Subject"] = "Bluff Royale feedback"
    email.set_content(message)

    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            if SMTP_USERNAME:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(email)
        return

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.starttls()
        if SMTP_USERNAME:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(email)


@router.post("")
async def send_feedback(body: FeedbackRequest, request: Request):
    _require_same_origin(request)
    if not SMTP_HOST:
        raise HTTPException(
            status_code=503,
            detail="Feedback email delivery is not configured on the server yet.",
        )
    if (SMTP_USERNAME and not SMTP_PASSWORD) or (SMTP_PASSWORD and not SMTP_USERNAME):
        raise HTTPException(
            status_code=503,
            detail="Feedback email credentials are incomplete on the server.",
        )
    now = time.monotonic()
    with _feedback_lock:
        while _feedback_sent_at and now - _feedback_sent_at[0] >= 60:
            _feedback_sent_at.popleft()
        if len(_feedback_sent_at) >= 5:
            raise HTTPException(
                status_code=429,
                detail="Too many feedback submissions. Please try again in a minute.",
            )
        _feedback_sent_at.append(now)

    try:
        await run_in_threadpool(_send_feedback, body.message.strip())
    except (OSError, smtplib.SMTPException) as error:
        logger.exception("Could not deliver site feedback email.")
        raise HTTPException(
            status_code=502,
            detail="Feedback could not be delivered. Please try again later.",
        ) from error
    return {"sent": True}
