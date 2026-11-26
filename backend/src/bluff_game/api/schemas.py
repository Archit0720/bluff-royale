from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..card import Rank
class StrictRequest(BaseModel):model_config=ConfigDict(extra='forbid')
class NameRequest(StrictRequest):player_name:str=Field(min_length=1,max_length=30)
class CreateRoomRequest(NameRequest):deck_count:int=Field(default=1,ge=1,le=3)
class ActionRequest(StrictRequest):pass
class PlayRequest(ActionRequest):card_indices:list[int]=Field(min_length=1);claimed_rank:Rank|None=None
class EmoteRequest(StrictRequest):
    emote: Literal[
        "laugh", "wow", "clap", "heart", "bluff", "cool", "fire", "crown", "eyes", "sweat", "shrug"
    ]


class DialogueRequest(StrictRequest):
    dialogue: Literal[
        "arre_bhai",
        "kya_scene",
        "filmi_bluff",
        "chai_break",
        "seedha_bol",
        "wah_ustad",
        "dimaag_laga",
        "jugaad_pro",
        "balle_balle",
        "shabaash_sher",
        "rangey_haath",
        "kya_baat",
        "boss_move",
        "scene_set",
    ] | None = None
    custom_text: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("custom_text")
    @classmethod
    def normalize_custom_text(cls, value):
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Custom table talk cannot be blank.")
        return value

    @model_validator(mode="after")
    def require_one_message(self):
        if (self.dialogue is None) == (self.custom_text is None):
            raise ValueError("Choose one preset line or provide custom table talk.")
        return self
