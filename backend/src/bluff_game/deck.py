import random
from .card import Card,Rank,Suit
class Deck:
 def __init__(self,count=1):
  if type(count)is not int or not 1<=count<=3:raise ValueError('The number of decks must be between 1 and 3.')
  self.cards=[Card(r,s) for _ in range(count) for s in Suit for r in Rank]
 def shuffle(self,rng=None):(rng or random).shuffle(self.cards)
 def deal(self,n):
  if not 2<=n<=6:raise ValueError('Bluff requires 2 to 6 players.')
  h=[[] for _ in range(n)]
  for i,c in enumerate(self.cards):h[i%n].append(c)
  return h
