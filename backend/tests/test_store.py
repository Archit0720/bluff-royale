import pytest
from bluff_game.storage.room_store import MemoryRoomStore
@pytest.mark.asyncio
async def test_memory_store():
 s=MemoryRoomStore();await s.set('A',{'x':1},10);assert(await s.get('A'))['x']==1
