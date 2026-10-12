from typing import Optional

from pydantic import BaseModel, Field


class TeamCreate(BaseModel):
    """
    Defines the information required to create a team.

    A team belongs to one club.

    Examples:
        Senior Men
        Senior Women
        U18
        U16
        Development XV
    """

    # Official team name
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Team name",
    )

    # General category of the team
    #
    # Examples:
    # senior
    # youth
    # development
    # academy
    category: str = Field(
        default="senior",
        max_length=50,
    )

    # Age group when applicable
    #
    # Examples:
    # Open
    # U18
    # U16
    # U14
    age_group: Optional[str] = Field(
        default=None,
        max_length=30,
    )

    # Gender category
    #
    # Examples:
    # male
    # female
    # mixed
    gender: Optional[str] = Field(
        default=None,
        max_length=30,
    )

    # Sporting season
    #
    # Example:
    # 2026
    # 2026/27
    season: Optional[str] = Field(
        default=None,
        max_length=20,
    )

    # Optional Firebase UID of the team's coach
    coach_uid: Optional[str] = Field(
        default=None,
        max_length=200,
    )


class TeamResponse(BaseModel):
    """
    Standard team information returned by the API.
    """

    team_id: str
    club_id: str
    name: str
    category: str
    age_group: Optional[str] = None
    gender: Optional[str] = None
    season: Optional[str] = None
    coach_uid: Optional[str] = None
    status: str
    created_by_uid: str


class TeamPlayerResponse(BaseModel):
    """
    Represents a player as part of a team's roster.
    """

    player_id: str
    team_id: str
    club_id: str
    full_name: str
    jersey_number: Optional[int] = None
    playing_position: Optional[str] = None
    status: str


class TeamDetailsResponse(TeamResponse):
    """
    Provides team information together with the number of
    currently assigned players.
    """

    player_count: int = 0