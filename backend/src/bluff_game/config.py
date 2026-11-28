import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bluff_history.db")
ROOM_TTL_SECONDS = int(os.getenv("ROOM_TTL_SECONDS", "86400"))
TURN_SECONDS = int(os.getenv("TURN_SECONDS", "40"))

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173",
)
ALLOWED_ORIGINS = list(
    dict.fromkeys(
        origin
        for origin in (
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            FRONTEND_URL,
        )
        if origin
    )
)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") or None
ANALYTICS_ADMIN_EMAIL = os.getenv(
    "ANALYTICS_ADMIN_EMAIL",
    "architdogra07@gmail.com",
).strip().casefold()
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FEEDBACK_TO_EMAIL = os.getenv(
    "FEEDBACK_TO_EMAIL",
    "architdogra95@gmail.com",
).strip()
APP_ENV = os.getenv("APP_ENV", "development").lower()
SESSION_COOKIE_NAME = "bluff_session"
SESSION_COOKIE_SAMESITE = "lax"