import time
from dataclasses import asdict
from fastapi import APIRouter,HTTPException,Request
from .schemas import NameRequest,ActionRequest,PlayRequest
router=APIRouter(prefix='/games',tags=['games'])
def manager(req):return req.app.state.manager
def fail(e):return HTTPException(404 if isinstance(e,KeyError)else 409,str(e.args[0]if isinstance(e,KeyError)else e))
def state(room,pid):
 d=room.game.visible_state(pid);d.update({'room_code':room.id,'paused':room.paused,'paused_by':room.paused_by,'turn_seconds_left':room.paused_seconds_left if room.paused else max(0,int((room.turn_deadline or time.time())-time.time()))});return d
@router.post('')
async def create(b:NameRequest,request:Request):
 r,p=await manager(request).create(b.player_name);return{'game_id':r.id,'player_id':p.id,'player_name':p.name}
@router.get('/history/{player_name}')
async def history(player_name:str,request:Request):return manager(request).history.by_player(player_name)
@router.get('/{gid}')
async def room(gid:str,request:Request):
 try:
  r=await manager(request).get(gid);return{'game_id':r.id,'status':r.status,'paused':r.paused,'players':[{'id':p.id,'name':p.name,'card_count':p.card_count}for p in r.players]}
 except Exception as e:raise fail(e)
@router.post('/{gid}/join')
async def join(gid:str,b:NameRequest,request:Request):
 try:
  p=await manager(request).join(gid,b.player_name);return{'game_id':gid.upper(),'player_id':p.id,'player_name':p.name}
 except Exception as e:raise fail(e)
@router.post('/{gid}/start')
async def start(gid:str,request:Request):
 try:
  r=await manager(request).start(gid);return state(r,r.game.current_player.id)
 except Exception as e:raise fail(e)
@router.get('/{gid}/players/{pid}')
async def private(gid:str,pid:str,request:Request):
 try:return state(await manager(request).get(gid),pid)
 except Exception as e:raise fail(e)
@router.post('/{gid}/play')
async def play(gid:str,b:PlayRequest,request:Request):
 try:
  m=manager(request);r=await m.get(gid)
  if r.paused:raise RuntimeError('Game is paused.')
  x=r.game.play(b.player_id,b.card_indices,b.claimed_rank);await m.action_done(r);return{'card_count':len(x.cards),'claimed_rank':x.claimed_rank.value}
 except Exception as e:raise fail(e)
@router.post('/{gid}/skip')
async def skip(gid:str,b:ActionRequest,request:Request):
 try:
  m=manager(request);r=await m.get(gid)
  if r.paused:raise RuntimeError('Game is paused.')
  x=r.game.skip(b.player_id);await m.action_done(r);return asdict(x)
 except Exception as e:raise fail(e)
@router.post('/{gid}/challenge')
async def challenge(gid:str,b:ActionRequest,request:Request):
 try:
  m=manager(request);r=await m.get(gid)
  if r.paused:raise RuntimeError('Game is paused.')
  x=r.game.challenge(b.player_id);await m.action_done(r);d=asdict(x);d['revealed_cards']=[str(c)for c in x.revealed_cards];return d
 except Exception as e:raise fail(e)
@router.post('/{gid}/pause')
async def pause(gid:str,b:ActionRequest,request:Request):
 try:
  m=manager(request);r=await m.get(gid);await m.pause(r,b.player_id);return{'paused':True,'paused_by':b.player_id}
 except Exception as e:raise fail(e)
@router.post('/{gid}/resume')
async def resume(gid:str,b:ActionRequest,request:Request):
 try:
  m=manager(request);r=await m.get(gid);await m.resume(r,b.player_id);return{'paused':False}
 except Exception as e:raise fail(e)
