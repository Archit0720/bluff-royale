from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..card import Rank
class StrictRequest(BaseModel):model_config=ConfigDict(extra='forbid')
class NameRequest(StrictRequest):player_name:str=Field(min_length=1,max_length=30)
class ActionRequest(StrictRequest):pass
class PlayRequest(ActionRequest):card_indices:list[int]=Field(min_length=1);claimed_rank:Rank|None=None
class EmoteRequest(StrictRequest):
    emote: Literal[
        "laugh", "wow", "clap", "heart", "bluff", "cool", "fire", "crown", "eyes", "sweat", "shrug"
    ]


class DialogueRequest(StrictRequest):
    dialogue: Literal[
        "bold_move",
        "prove_it",
        "eyes_on_you",
        "nice_try",
        "royal_bluff",
        "well_played",
        "calculated",
        "plot_twist",
        "no_way",
        "ice_cold",
        "crown_jewel",
        "read_the_table",
        "almost_had_me",
        "respect_the_play",
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
