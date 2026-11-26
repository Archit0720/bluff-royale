from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import (
    ALLOWED_ORIGINS,
    DATABASE_URL,
    GOOGLE_CLIENT_ID,
    REDIS_URL,
    USE_MEMORY_STORE,
)
from ..auth import AuthService
from ..history import History
from ..storage.room_store import MemoryRoomStore, RedisRoomStore
from .manager import Manager
from .routes import router
from .auth_routes import router as auth_router


@asynccontextmanager
async def lifespan(app):
    store = (
        MemoryRoomStore()
        if USE_MEMORY_STORE
        else RedisRoomStore(REDIS_URL)
    )

    if hasattr(store, "ping"):
        await store.ping()

    history = History(DATABASE_URL)
    app.state.history = history
    app.state.auth = AuthService(history.Session, GOOGLE_CLIENT_ID)
    app.state.manager = Manager(store, history)

    yield

    if hasattr(store, "close"):
        await store.close()


app = FastAPI(
    title="Bluff Royale API",
    version="0.6.0",
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


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "0.6.0",
    }