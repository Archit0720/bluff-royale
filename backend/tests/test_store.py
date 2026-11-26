import time

import pytest
from bluff_game.storage.room_store import MemoryRoomStore
@pytest.mark.asyncio
async def test_memory_store():
 s=MemoryRoomStore();await s.set('A',{'x':1},10);assert(await s.get('A'))['x']==1
 event={'player_id':'p1','emote':'clap','created_at':time.time()}
 await s.publish_emote('A',event)
 assert await s.recent_emotes('A')==[event]
 await s.touch_presence('A','p1')
 assert(await s.room_presence('A'))['p1']=='online'
 await s.mark_left('A','p1')
 await s.touch_presence('A','p1')
 assert(await s.room_presence('A'))['p1']=='left'
 await s.delete('A')
 assert await s.room_presence('A')=={}
