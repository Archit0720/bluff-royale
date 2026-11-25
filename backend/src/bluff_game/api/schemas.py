from pydantic import BaseModel,Field
from ..card import Rank
class NameRequest(BaseModel):player_name:str=Field(min_length=1,max_length=30)
class ActionRequest(BaseModel):player_id:str
class PlayRequest(ActionRequest):card_indices:list[int]=Field(min_length=1);claimed_rank:Rank|None=None
