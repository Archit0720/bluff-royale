from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import (
    DATABASE_URL,
    REDIS_URL,
    USE_MEMORY_STORE,
    FRONTEND_URL,
)
from ..history import History
from ..storage.room_store import MemoryRoomStore, RedisRoomStore
from .manager import Manager
from .routes import router


@asynccontextmanager
async def lifespan(app):
    store = (
        MemoryRoomStore()
        if USE_MEMORY_STORE
        else RedisRoomStore(REDIS_URL)
    )

    if hasattr(store, "ping"):
        await store.ping()

    app.state.manager = Manager(
        store,
        History(DATABASE_URL),
    )

    yield

    if hasattr(store, "close"):
        await store.close()


app = FastAPI(
    title="Bluff Royale API",
    version="0.6.0",
    lifespan=lifespan,
)


allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    FRONTEND_URL,
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "0.6.0",
    }