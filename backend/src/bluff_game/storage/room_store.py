import pickle
from abc import ABC,abstractmethod
from redis.asyncio import Redis
class RoomStore(ABC):
 @abstractmethod
 async def get(self,key):...
 @abstractmethod
 async def set(self,key,value,ttl):...
 @abstractmethod
 async def delete(self,key):...
class MemoryRoomStore(RoomStore):
 def __init__(self):self.data={}
 async def get(self,key):return self.data.get(key)
 async def set(self,key,value,ttl):self.data[key]=value
 async def delete(self,key):self.data.pop(key,None)
class RedisRoomStore(RoomStore):
 def __init__(self,url):self.client=Redis.from_url(url)
 async def ping(self):return await self.client.ping()
 async def close(self):await self.client.aclose()
 async def get(self,key):
  raw=await self.client.get(f'bluff:room:{key}');return pickle.loads(raw) if raw else None
 async def set(self,key,value,ttl):await self.client.set(f'bluff:room:{key}',pickle.dumps(value),ex=ttl)
 async def delete(self,key):await self.client.delete(f'bluff:room:{key}')
