import os
REDIS_URL=os.getenv('REDIS_URL','redis://localhost:6379/0')
DATABASE_URL=os.getenv('DATABASE_URL','sqlite:///./bluff_history.db')
ROOM_TTL_SECONDS=int(os.getenv('ROOM_TTL_SECONDS','86400'))
TURN_SECONDS=int(os.getenv('TURN_SECONDS','40'))
USE_MEMORY_STORE=os.getenv('USE_MEMORY_STORE','false').lower()=='true'
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")