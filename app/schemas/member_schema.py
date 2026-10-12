from typing import Optional

from pydantic import BaseModel, Field


class MemberAdd(BaseModel):
    """
    Defines the information required to add an existing
    authenticated Firebase user to a club.

    The Firebase UID comes from the request because the
    club administrator selects which authenticated user
    should be added.

    IMPORTANT:
    The backend still validates the requester's permissions.
    """

    # Firebase UID of the user being added to the club
    uid: str = Field(
        ...,
        min_length=1,
        max_length=200,
    )

    # Role the new member will have in the club
    role: str = Field(
        ...,
        min_length=3,
        max_length=30,
    )

    # Optional display name
    display_name: Optional[str] = Field(
        default=None,
        max_length=150,
    )

    # Optional email address
    email: Optional[str] = Field(
        default=None,
        max_length=200,
    )


class MemberRoleUpdate(BaseModel):
    """
    Defines the information required to change
    an existing member's role.
    """

    # New club role
    role: str = Field(
        ...,
        min_length=3,
        max_length=30,
    )


class MemberResponse(BaseModel):
    """
    Standard member information returned by the API.
    """

    uid: str
    club_id: str
    role: str
    status: str
    display_name: Optional[str] = None
    email: Optional[str] = None