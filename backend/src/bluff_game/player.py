from dataclasses import dataclass,field
from .card import Card,Rank
ORDER={r:i for i,r in enumerate(Rank)}
@dataclass(slots=True)
class Player:
 id:str;name:str;hand:list[Card]=field(default_factory=list)
 @property
 def card_count(self):return len(self.hand)
 def sort_hand(self):self.hand.sort(key=lambda c:(ORDER[c.rank],c.suit.value))
 def play_cards(self,indices):
  if not indices:raise ValueError('Select at least one card.')
  if len(indices)!=len(set(indices)):raise ValueError('The same card cannot be selected twice.')
  if any(i<0 or i>=len(self.hand) for i in indices):raise IndexError('Invalid card index.')
  cards=[self.hand[i] for i in indices]
  for i in sorted(indices,reverse=True):self.hand.pop(i)
  return cards
 def receive_cards(self,cards):self.hand.extend(cards);self.sort_hand()
