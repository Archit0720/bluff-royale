import asyncio
import json
import pickle
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager

from redis.asyncio import Redis

EMOTE_TTL_SECONDS = 30
EMOTE_LIMIT = 18


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


class MemoryRoomStore(RoomStore):
    def __init__(self):
        self.data = {}
        self.locks = {}
        self.emotes = {}

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, ttl):
        self.data[key] = value

    async def delete(self, key):
        self.data.pop(key, None)

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

    @asynccontextmanager
    async def room_lock(self, key):
        lock = self.locks.setdefault(key, asyncio.Lock())
        async with lock:
            yield


class RedisRoomStore(RoomStore):
    def __init__(self, url):
        self.client = Redis.from_url(url)

    async def ping(self):
        return await self.client.ping()

    async def close(self):
        await self.client.aclose()

    async def get(self, key):
        raw = await self.client.get(f"bluff:room:{key}")
        return pickle.loads(raw) if raw else None

    async def set(self, key, value, ttl):
        await self.client.set(f"bluff:room:{key}", pickle.dumps(value), ex=ttl)

    async def delete(self, key):
        await self.client.delete(f"bluff:room:{key}")

    async def publish_emote(self, key, event):
        redis_key = f"bluff:room-emotes:{key}"
        async with self.client.pipeline(transaction=True) as pipeline:
            await (
                pipeline.lpush(redis_key, json.dumps(event))
                .ltrim(redis_key, 0, EMOTE_LIMIT - 1)
                .expire(redis_key, EMOTE_TTL_SECONDS)
                .execute()
            )

    async def recent_emotes(self, key):
        entries = await self.client.lrange(
            f"bluff:room-emotes:{key}",
            0,
            EMOTE_LIMIT - 1,
        )
        return [json.loads(entry) for entry in entries]

    @asynccontextmanager
    async def room_lock(self, key):
        async with self.client.lock(
            f"bluff:room-lock:{key}",
            timeout=30,
            blocking_timeout=30,
        ):
            yield
