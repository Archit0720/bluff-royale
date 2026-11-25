import random
from .card import Card,Rank,Suit
class Deck:
 def __init__(self):self.cards=[Card(r,s) for s in Suit for r in Rank]
 def shuffle(self,rng=None):(rng or random).shuffle(self.cards)
 def deal(self,n):
  if not 2<=n<=6:raise ValueError('Bluff requires 2 to 6 players.')
  h=[[] for _ in range(n)]
  for i,c in enumerate(self.cards):h[i%n].append(c)
  return h
