from dataclasses import dataclass
from enum import Enum
class Suit(str,Enum): CLUBS='Clubs';DIAMONDS='Diamonds';HEARTS='Hearts';SPADES='Spades'
class Rank(str,Enum): ACE='A';TWO='2';THREE='3';FOUR='4';FIVE='5';SIX='6';SEVEN='7';EIGHT='8';NINE='9';TEN='10';JACK='J';QUEEN='Q';KING='K'
@dataclass(frozen=True,slots=True)
class Card:
 rank:Rank;suit:Suit
 def __str__(self):return f"{self.rank.value}{ {Suit.CLUBS:'C',Suit.DIAMONDS:'D',Suit.HEARTS:'H',Suit.SPADES:'S'}[self.suit]}"
