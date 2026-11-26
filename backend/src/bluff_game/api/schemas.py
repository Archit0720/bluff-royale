from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..card import Rank
class StrictRequest(BaseModel):model_config=ConfigDict(extra='forbid')
class NameRequest(StrictRequest):player_name:str=Field(min_length=1,max_length=30)
class ActionRequest(StrictRequest):pass
class PlayRequest(ActionRequest):card_indices:list[int]=Field(min_length=1);claimed_rank:Rank|None=None
class EmoteRequest(StrictRequest):emote:Literal["laugh","wow","clap","heart","bluff"]
class DialogueRequest(StrictRequest):dialogue:Literal["bold_move","prove_it","eyes_on_you","nice_try","royal_bluff","well_played"]
