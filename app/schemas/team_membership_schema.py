"""
Schemas for team memberships.

A membership connects a Firebase user to a specific rugby team.

Supported team roles:

    team_manager
    coach

Executives create these memberships.
"""

from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field


class TeamMembershipCreate(BaseModel):
    """
    Data required when an Executive assigns a user
    to a team.
    """

    user_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
    )

    role: Literal[
        "team_manager",
        "coach",
    ] = "team_manager"


class TeamMembershipResponse(BaseModel):
    """Returned representation of a team membership."""

    membership_id: str

    team_id: str

    user_id: str

    role: str

    status: str

    created_at: Optional[datetime] = None

    created_by: Optional[str] = None