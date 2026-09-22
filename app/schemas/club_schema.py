from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class ClubCreate(BaseModel):
    """
    Data required when registering a new club.

    The authenticated user's UID is obtained from Firebase.
    It must not be submitted by the frontend.
    """

    name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Official rugby club name",
    )

    registration_number: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Club registration or affiliation number",
    )

    email: EmailStr = Field(
        ...,
        description="Official club email address",
    )

    phone: Optional[str] = Field(
        default=None,
        max_length=30,
        description="Club contact telephone number",
    )

    address: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Club address",
    )


class ClubResponse(BaseModel):
    """
    Standard club information returned by the API.
    """

    club_id: str
    name: str
    registration_number: Optional[str] = None
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    created_by_uid: str
    status: str


class ClubMemberResponse(BaseModel):
    """
    Represents a user's membership in a club.
    """

    uid: str
    role: str
    status: str


class ClubDetailsResponse(ClubResponse):
    """
    Provides club information together with the user's membership role.
    """

    membership: ClubMemberResponse