import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bluff_history.db")
ROOM_TTL_SECONDS = int(os.getenv("ROOM_TTL_SECONDS", "86400"))
TURN_SECONDS = int(os.getenv("TURN_SECONDS", "40"))
USE_MEMORY_STORE = os.getenv("USE_MEMORY_STORE", "false").lower() == "true"

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
APP_ENV = os.getenv("APP_ENV", "development").lower()
SESSION_COOKIE_NAME = "bluff_session"
SESSION_COOKIE_SAMESITE = "none" if APP_ENV == "production" else "lax"