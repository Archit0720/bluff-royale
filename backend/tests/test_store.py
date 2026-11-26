import time

import pytest
from bluff_game.storage.room_store import MemoryRoomStore
@pytest.mark.asyncio
async def test_memory_store():
 s=MemoryRoomStore();await s.set('A',{'x':1},10);assert(await s.get('A'))['x']==1
 event={'player_id':'p1','emote':'clap','created_at':time.time()}
 await s.publish_emote('A',event)
 assert await s.recent_emotes('A')==[event]
