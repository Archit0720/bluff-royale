import random
from dataclasses import dataclass
from enum import Enum
from .card import Card,Rank,Suit
from .deck import Deck
from .player import Player
class GameStatus(str,Enum):WAITING='waiting';PLAYING='playing';FINISHED='finished'
@dataclass(frozen=True,slots=True)
class Play:
 player_id:str;cards:tuple[Card,...];claimed_rank:Rank
 @property
 def was_bluff(self):return any(c.rank!=self.claimed_rank for c in self.cards)
@dataclass(frozen=True,slots=True)
class ChallengeResult:challenger_id:str;challenged_player_id:str;was_bluff:bool;loser_id:str;picked_up_count:int;revealed_cards:tuple[Card,...];next_round_starter_id:str|None;newly_finished_ids:tuple[str,...]
@dataclass(frozen=True,slots=True)
class SkipResult:player_id:str;round_ended:bool;discarded_count:int;next_player_id:str|None;newly_finished_ids:tuple[str,...]
class BluffGame:
 def __init__(self,players):
  if not 2<=len(players)<=6:raise ValueError('Bluff requires 2 to 6 players.')
  self.players=players;self.status=GameStatus.WAITING;self.current_player_index=0;self.current_rank=None;self.pile=[];self.discard_pile=[];self.last_play=None;self.skipped_since_last_play=set();self.provisional_finishers=[];self.finishing_order=[];self.event_log=[]
 @property
 def current_player(self):return self.players[self.current_player_index]
 @property
 def active_players(self):return[p for p in self.players if p.id not in self.finishing_order and p.id not in self.provisional_finishers]
 @property
 def last_place_id(self):return self.finishing_order[-1] if self.status==GameStatus.FINISHED else None
 def start(self,seed=None):
  d=Deck();d.shuffle(random.Random(seed));hands=d.deal(len(self.players))
  for p,h in zip(self.players,hands,strict=True):p.hand=h;p.sort_hand()
  ace=Card(Rank.ACE,Suit.SPADES);self.current_player_index=next(i for i,p in enumerate(self.players)if ace in p.hand);self.status=GameStatus.PLAYING;self.event_log.append({'type':'start','player_id':self.current_player.id})
 def play(self,pid,indices,rank=None):
  self._turn(pid)
  if self.current_rank is None:
   if rank is None:raise ValueError('The round starter must choose a claimed rank.')
   self.current_rank=rank
  elif rank is not None and rank!=self.current_rank:raise ValueError('The claimed rank cannot change during an active round.')
  p=self.current_player;cards=p.play_cards(indices);play=Play(pid,tuple(cards),self.current_rank);self._confirm_except(pid);self.pile.extend(cards);self.last_play=play;self.skipped_since_last_play.clear()
  if p.card_count==0 and pid not in self.provisional_finishers:self.provisional_finishers.append(pid)
  self.event_log.append({'type':'play','player_id':pid,'count':len(cards),'rank':self.current_rank.value});self._advance();return play
 def skip(self,pid):
  self._turn(pid)
  if self.last_play is None:raise RuntimeError('The round starter cannot skip before any cards are played.')
  newly=self._confirm_except(self.last_play.player_id);self.skipped_since_last_play.add(pid);self.event_log.append({'type':'skip','player_id':pid});last=self.last_play.player_id;required={p.id for p in self.active_players if p.id!=last}
  if required.issubset(self.skipped_since_last_play):
   n=len(self.pile);self.discard_pile.extend(self.pile);self.pile.clear();newly+=self._confirm_all()
   if self._complete():return SkipResult(pid,True,n,None,tuple(newly))
   starter=last if self._eligible(last) else self._next(last).id;self._new_round(starter);return SkipResult(pid,True,n,starter,tuple(newly))
  self._advance();return SkipResult(pid,False,0,self.current_player.id,tuple(newly))
 def challenge(self,pid):
  self._turn(pid)
  if self.last_play is None:raise RuntimeError('There is no play to challenge.')
  challenged=self.last_play;bluff=challenged.was_bluff;loser=challenged.player_id if bluff else pid;starter=pid if bluff else challenged.player_id;n=len(self.pile);self.get_player(loser).receive_cards(self.pile);self.pile.clear()
  if loser in self.provisional_finishers:self.provisional_finishers.remove(loser)
  newly=self._confirm_all();self.event_log.append({'type':'challenge','challenger_id':pid,'challenged_id':challenged.player_id,'was_bluff':bluff,'loser_id':loser,'pile':n});next_starter=None
  if not self._complete():next_starter=starter if self._eligible(starter)else self._next(starter).id;self._new_round(next_starter)
  return ChallengeResult(pid,challenged.player_id,bluff,loser,n,challenged.cards,next_starter,tuple(newly))
 def available_actions(self,pid):
  if self.status!=GameStatus.PLAYING or self.current_player.id!=pid:return[]
  return['play']if self.last_play is None else['play','challenge','skip']
 def visible_state(self,pid):
  v=self.get_player(pid);return{'status':self.status.value,'current_rank':self.current_rank.value if self.current_rank else None,'current_player_id':self.current_player.id if self.status==GameStatus.PLAYING else None,'pile_size':len(self.pile),'discarded_count':len(self.discard_pile),'last_play':None if not self.last_play else{'player_id':self.last_play.player_id,'card_count':len(self.last_play.cards),'claimed_rank':self.last_play.claimed_rank.value},'skipped_player_ids':sorted(self.skipped_since_last_play),'provisional_finishers':list(self.provisional_finishers),'finishing_order':list(self.finishing_order),'last_place_id':self.last_place_id,'available_actions':self.available_actions(pid),'players':[{'id':p.id,'name':p.name,'card_count':p.card_count,'position':self.finishing_order.index(p.id)+1 if p.id in self.finishing_order else None,'provisional':p.id in self.provisional_finishers}for p in self.players],'your_hand':[str(c)for c in v.hand],'recent_events':self.event_log[-8:]}
 def get_player(self,pid):
  for p in self.players:
   if p.id==pid:return p
  raise KeyError('Unknown player ID.')
 def _turn(self,pid):
  if self.status!=GameStatus.PLAYING:raise RuntimeError('The game is not active.')
  if self.current_player.id!=pid:raise ValueError("It is not this player's turn.")
 def _eligible(self,pid):return pid not in self.finishing_order and pid not in self.provisional_finishers
 def _next(self,pid):
  i=next(i for i,p in enumerate(self.players)if p.id==pid)
  for x in range(1,len(self.players)+1):
   p=self.players[(i+x)%len(self.players)]
   if self._eligible(p.id):return p
  raise RuntimeError('No active player remains.')
 def _advance(self):self.current_player_index=self.players.index(self._next(self.current_player.id))
 def _set(self,pid):self.current_player_index=next(i for i,p in enumerate(self.players)if p.id==pid)
 def _confirm_except(self,target):
  out=[]
  for pid in list(self.provisional_finishers):
   if pid!=target:self.provisional_finishers.remove(pid);self.finishing_order.append(pid);out.append(pid)
  self._complete();return out
 def _confirm_all(self):
  out=[]
  for pid in list(self.provisional_finishers):self.provisional_finishers.remove(pid);self.finishing_order.append(pid);out.append(pid)
  return out
 def _complete(self):
  remaining=[p.id for p in self.players if p.id not in self.finishing_order and p.id not in self.provisional_finishers]
  if len(remaining)==1 and len(self.finishing_order)+len(self.provisional_finishers)==len(self.players)-1:
   self._confirm_all();remaining=[p.id for p in self.players if p.id not in self.finishing_order]
   if len(remaining)==1:self.finishing_order.append(remaining[0])
   self.status=GameStatus.FINISHED;self.current_rank=None;self.last_play=None;self.skipped_since_last_play.clear();self.event_log.append({'type':'finished'});return True
  return False
 def _new_round(self,pid):self.current_rank=None;self.last_play=None;self.skipped_since_last_play.clear();self._set(pid);self.event_log.append({'type':'new_round','player_id':pid})
