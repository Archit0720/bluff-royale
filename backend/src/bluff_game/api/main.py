from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import (
    ALLOWED_ORIGINS,
    DATABASE_URL,
    GOOGLE_CLIENT_ID,
)
from ..auth import AuthService
from ..history import History
from ..storage.room_store import MemoryRoomStore
from .manager import Manager
from .routes import router
from .auth_routes import router as auth_router
from .analytics_routes import router as analytics_router
from .feedback_routes import router as feedback_router


@asynccontextmanager
async def lifespan(app):
    store = MemoryRoomStore()
    history = History(DATABASE_URL)
    app.state.history = history
    app.state.auth = AuthService(history.Session, GOOGLE_CLIENT_ID)
    app.state.manager = Manager(store, history)

    yield


app = FastAPI(
    title="Bluff Royale API",
    version="0.7.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)
app.include_router(auth_router)
app.include_router(analytics_router)
app.include_router(feedback_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "0.7.0",
        "room_storage": "memory",
    }