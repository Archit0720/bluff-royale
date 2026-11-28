import asyncio
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager

EMOTE_TTL_SECONDS = 30
EMOTE_LIMIT = 18
PRESENCE_TTL_SECONDS = 12


class RoomStore(ABC):
    @abstractmethod
    async def get(self, key):
        ...

    @abstractmethod
    async def set(self, key, value, ttl):
        ...

    @abstractmethod
    async def delete(self, key):
        ...

    @abstractmethod
    async def publish_emote(self, key, event):
        ...

    @abstractmethod
    async def recent_emotes(self, key):
        ...

    @abstractmethod
    async def touch_presence(self, key, player_id):
        ...

    @abstractmethod
    async def mark_left(self, key, player_id):
        ...

    @abstractmethod
    async def room_presence(self, key):
        ...


class MemoryRoomStore(RoomStore):
    def __init__(self):
        self.data = {}
        self.expirations = {}
        self.locks = {}
        self.emotes = {}
        self.presence = {}

    async def get(self, key):
        expires_at = self.expirations.get(key)
        if expires_at is not None and expires_at <= time.time():
            await self.delete(key)
            return None
        return self.data.get(key)

    async def set(self, key, value, ttl):
        self.data[key] = value
        self.expirations[key] = time.time() + ttl

    async def delete(self, key):
        self.data.pop(key, None)
        self.expirations.pop(key, None)
        self.emotes.pop(key, None)
        self.presence.pop(key, None)

    async def publish_emote(self, key, event):
        recent = [
            item
            for item in self.emotes.get(key, [])
            if item["created_at"] > time.time() - EMOTE_TTL_SECONDS
        ]
        recent.insert(0, event)
        self.emotes[key] = recent[:EMOTE_LIMIT]

    async def recent_emotes(self, key):
        recent = [
            item
            for item in self.emotes.get(key, [])
            if item["created_at"] > time.time() - EMOTE_TTL_SECONDS
        ]
        self.emotes[key] = recent
        return recent

    async def touch_presence(self, key, player_id):
        room = self.presence.setdefault(key, {})
        current = room.get(player_id)
        if current is None or current["status"] != "left":
            room[player_id] = {"status": "online", "at": time.time()}

    async def mark_left(self, key, player_id):
        self.presence.setdefault(key, {})[player_id] = {
            "status": "left",
            "at": time.time(),
        }

    async def room_presence(self, key):
        now = time.time()
        return {
            player_id: (
                "left"
                if event["status"] == "left"
                or now - event["at"] > PRESENCE_TTL_SECONDS
                else "online"
            )
            for player_id, event in self.presence.get(key, {}).items()
        }

    @asynccontextmanager
    async def room_lock(self, key):
        lock = self.locks.setdefault(key, asyncio.Lock())
        async with lock:
            yield
