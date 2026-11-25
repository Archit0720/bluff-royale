import secrets,time
from dataclasses import dataclass
from ..config import ROOM_TTL_SECONDS,TURN_SECONDS
from ..game import BluffGame,GameStatus
from ..player import Player
A='ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
@dataclass
class Room:
 id:str;players:list[Player];creator_id:str;game:BluffGame|None=None;paused:bool=False;paused_by:str|None=None;turn_deadline:float|None=None;paused_seconds_left:int|None=None;started_at:float=0;history_saved:bool=False
 @property
 def status(self):return self.game.status.value if self.game else GameStatus.WAITING.value
class Manager:
 def __init__(self,store,history):self.store=store;self.history=history
 async def save(self,r):await self.store.set(r.id,r,ROOM_TTL_SECONDS)
 async def get(self,gid):
  r=await self.store.get(gid.upper())
  if not r:raise KeyError('Game not found.')
  await self.apply_timeout(r);return r
 async def create(self,name):
  gid=''.join(secrets.choice(A)for _ in range(5));p=Player(secrets.token_urlsafe(12),name.strip());r=Room(gid,[p],p.id);await self.save(r);return r,p
 async def join(self,gid,name):
  r=await self.get(gid)
  if r.game:raise RuntimeError('Game already started.')
  if len(r.players)>=6:raise ValueError('Room is full.')
  if any(p.name.casefold()==name.strip().casefold()for p in r.players):raise ValueError('Name already used.')
  p=Player(secrets.token_urlsafe(12),name.strip());r.players.append(p);await self.save(r);return p
 async def start(self,gid):
  r=await self.get(gid)
  if len(r.players)<2:raise ValueError('At least 2 players are required.')
  r.game=BluffGame(r.players);r.game.start();r.started_at=time.time();self.reset_timer(r);await self.save(r);return r
 def reset_timer(self,r):r.turn_deadline=time.time()+TURN_SECONDS
 async def action_done(self,r):
  if r.game.status==GameStatus.FINISHED:self.history.save(r)
  else:self.reset_timer(r)
  await self.save(r)
 async def apply_timeout(self,r):
  if not r.game or r.paused or r.game.status!=GameStatus.PLAYING or not r.turn_deadline or time.time()<r.turn_deadline:return
  pid=r.game.current_player.id
  if r.game.last_play is not None:r.game.skip(pid);r.game.event_log.append({'type':'timeout_skip','player_id':pid});self.reset_timer(r)
  else:r.paused=True;r.paused_by='system';r.paused_seconds_left=TURN_SECONDS;r.turn_deadline=None;r.game.event_log.append({'type':'timeout_pause','player_id':pid})
  if r.game.status==GameStatus.FINISHED:self.history.save(r)
  await self.save(r)
 async def pause(self,r,pid):
  if r.paused:raise RuntimeError('Game is already paused.')
  r.paused=True;r.paused_by=pid;r.paused_seconds_left=max(1,int((r.turn_deadline or time.time())-time.time()));r.turn_deadline=None;await self.save(r)
 async def resume(self,r,pid):
  if not r.paused:raise RuntimeError('Game is not paused.')
  r.paused=False;r.paused_by=None;r.turn_deadline=time.time()+(r.paused_seconds_left or TURN_SECONDS);r.paused_seconds_left=None;await self.save(r)
