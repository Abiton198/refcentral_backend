"""
Player Schemas

Defines the data used to register and manage players.

Important:
- The player's permanent profile lives in the players collection.
- Match-specific information will live under an appointment squad.
- Identity documents are handled separately.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class PlayerCreate(BaseModel):
    """
    Data required to register a new player.
    """

    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    middle_name: Optional[str] = Field(
        default="",
        max_length=100,
    )

    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    date_of_birth: date

    gender: Optional[str] = Field(
        default=None,
        max_length=30,
    )

    position: Optional[str] = Field(
        default=None,
        max_length=50,
    )

    jersey_number: Optional[int] = Field(
        default=None,
        ge=1,
        le=99,
    )


class PlayerUpdate(BaseModel):
    """
    Fields that can be changed after registration.
    """

    first_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    middle_name: Optional[str] = Field(
        default=None,
        max_length=100,
    )

    last_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    date_of_birth: Optional[date] = None

    gender: Optional[str] = Field(
        default=None,
        max_length=30,
    )

    position: Optional[str] = Field(
        default=None,
        max_length=50,
    )

    jersey_number: Optional[int] = Field(
        default=None,
        ge=1,
        le=99,
    )

    status: Optional[str] = Field(
        default=None,
        max_length=30,
    )


class PlayerResponse(BaseModel):
    """
    Player information returned by the API.

    Identity-document information is intentionally excluded.
    """

    player_id: str
    team_id: str

    first_name: str
    middle_name: Optional[str] = None
    last_name: str

    date_of_birth: date

    gender: Optional[str] = None
    position: Optional[str] = None
    jersey_number: Optional[int] = None

    photo_url: Optional[str] = None

    status: str
    registration_status: str

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
