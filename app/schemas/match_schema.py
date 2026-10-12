from datetime import date, time
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------
# MATCH CREATION
# ---------------------------------------------------------
# This is the information required when a club creates
# a new fixture.
#
# The home team MUST belong to the current RefCentral club.
#
# The opposition can either:
#   1. Be another RefCentral team, using away_team_id
#   2. Simply be entered by name if the opposition is not
#      registered in RefCentral yet.
# ---------------------------------------------------------

class MatchCreate(BaseModel):
    home_team_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
    )

    away_team_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
    )

    # Optional if the opposition is already registered
    # inside RefCentral.
    away_team_id: Optional[str] = Field(
        default=None,
        max_length=200,
    )

    # Optional RefCentral club belonging to the opposition.
    # This becomes useful when we support cross-club fixtures.
    away_club_id: Optional[str] = Field(
        default=None,
        max_length=200,
    )

    match_date: date

    match_time: time

    venue: str = Field(
        ...,
        min_length=2,
        max_length=200,
    )

    competition: Optional[str] = Field(
        default=None,
        max_length=150,
    )

    season: Optional[str] = Field(
        default=None,
        max_length=30,
    )


# ---------------------------------------------------------
# MATCH UPDATE
# ---------------------------------------------------------
# Used when an administrator needs to change fixture
# information such as date, time, venue or opposition.
# ---------------------------------------------------------

class MatchUpdate(BaseModel):
    home_team_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    away_team_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    away_team_id: Optional[str] = Field(
        default=None,
        max_length=200,
    )

    away_club_id: Optional[str] = Field(
        default=None,
        max_length=200,
    )

    match_date: Optional[date] = None

    match_time: Optional[time] = None

    venue: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    competition: Optional[str] = Field(
        default=None,
        max_length=150,
    )

    season: Optional[str] = Field(
        default=None,
        max_length=30,
    )


# ---------------------------------------------------------
# MATCH RESPONSE
# ---------------------------------------------------------
# This is the structure returned to the frontend.
# ---------------------------------------------------------

class MatchResponse(BaseModel):
    match_id: str
    club_id: str

    home_team_id: str
    home_team_name: str

    away_team_id: Optional[str] = None
    away_team_name: str
    away_club_id: Optional[str] = None

    match_date: date
    match_time: time

    venue: str

    competition: Optional[str] = None
    season: Optional[str] = None

    # scheduled
    # in_progress
    # completed
    # cancelled
    status: str

    referee_uid: Optional[str] = None

    created_by_uid: str


# ---------------------------------------------------------
# REFEREE ASSIGNMENT
# ---------------------------------------------------------
# Referee assignment is kept separate from match creation.
# This gives us a cleaner workflow later when referee
# appointments become more sophisticated.
# ---------------------------------------------------------

class MatchRefereeAssign(BaseModel):
    referee_uid: str = Field(
        ...,
        min_length=1,
        max_length=200,
    )
