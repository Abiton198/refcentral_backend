from typing import Optional

from pydantic import BaseModel, Field


class PlayerCreate(BaseModel):
    """
    Defines the information required to register a rugby player.

    The frontend submits player details.
    The backend supplies:
    - player_id
    - registered_by_uid
    - timestamps
    - status
    """

    # Player's full legal name
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
    )

    # Date of birth in YYYY-MM-DD format
    date_of_birth: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Date of birth in YYYY-MM-DD format",
    )

    # Optional player registration or membership number
    registration_number: Optional[str] = Field(
        default=None,
        max_length=100,
    )

    # Rugby playing position
    playing_position: Optional[str] = Field(
        default=None,
        max_length=80,
    )

    # Jersey number, if assigned
    jersey_number: Optional[int] = Field(
        default=None,
        ge=1,
        le=99,
    )

    # Emergency contact person's name
    emergency_contact_name: Optional[str] = Field(
        default=None,
        max_length=150,
    )

    # Emergency contact telephone number
    emergency_contact_phone: Optional[str] = Field(
        default=None,
        max_length=30,
    )


class PlayerResponse(BaseModel):
    """
    Defines the information returned for a registered player.
    """

    player_id: str
    club_id: str
    full_name: str
    date_of_birth: str
    registration_number: Optional[str] = None
    playing_position: Optional[str] = None
    jersey_number: Optional[int] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    registered_by_uid: str
    status: str

class PlayerUpdate(BaseModel):
    """
    Defines the fields that can be changed after registration.

    All fields are optional so the frontend can update only
    the information that has changed.
    """

    # Updated player name
    full_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    # Updated date of birth
    date_of_birth: Optional[str] = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )

    # Updated registration number
    registration_number: Optional[str] = Field(
        default=None,
        max_length=100,
    )

    # Updated playing position
    playing_position: Optional[str] = Field(
        default=None,
        max_length=80,
    )

    # Updated jersey number
    jersey_number: Optional[int] = Field(
        default=None,
        ge=1,
        le=99,
    )

    # Updated emergency contact details
    emergency_contact_name: Optional[str] = Field(
        default=None,
        max_length=150,
    )

    emergency_contact_phone: Optional[str] = Field(
        default=None,
        max_length=30,
    )