from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class ClubCreate(BaseModel):
    """
    Defines the information required to register a new rugby club.

    Important:
    - created_by_uid is NOT accepted from the frontend.
    - The backend obtains the authenticated user's UID from Firebase.
    """

    # Official name of the rugby club
    name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Official rugby club name",
    )

    # Optional registration or affiliation number
    registration_number: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Club registration or affiliation number",
    )

    # Main club email address
    email: EmailStr = Field(
        ...,
        description="Official club email address",
    )

    # Contact telephone number
    phone: Optional[str] = Field(
        default=None,
        max_length=30,
        description="Club contact telephone number",
    )

    # Physical or postal address of the club
    address: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Club address",
    )


class ClubResponse(BaseModel):
    """
    Defines the format returned after a club is created.
    """

    # Firestore-generated document ID
    club_id: str

    # Club information
    name: str
    registration_number: Optional[str] = None
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None

    # UID of the authenticated user who created the club
    created_by_uid: str

    # Indicates whether the club is currently active
    status: str