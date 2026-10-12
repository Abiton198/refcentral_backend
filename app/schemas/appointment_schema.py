from datetime import date, time
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------
# APPOINTMENT CREATION
# ---------------------------------------------------------
# Appointments are created by executives.
#
# Both participating teams must already exist in the
# RefCentral teams collection.
# ---------------------------------------------------------

class AppointmentCreate(BaseModel):
    home_team_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
    )

    away_team_id: str = Field(
        ...,
        min_length=1,
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

    competition_type: Optional[str] = Field(
        default="club",
        max_length=50,
    )

    season: Optional[str] = Field(
        default=None,
        max_length=30,
    )

    team_level: Optional[str] = Field(
        default="main",
        max_length=50,
    )

    notes: Optional[str] = Field(
        default="",
        max_length=1000,
    )


# ---------------------------------------------------------
# APPOINTMENT UPDATE
# ---------------------------------------------------------
# Only executives should be able to update fixture details.
# ---------------------------------------------------------

class AppointmentUpdate(BaseModel):
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

    competition_type: Optional[str] = Field(
        default=None,
        max_length=50,
    )

    season: Optional[str] = Field(
        default=None,
        max_length=30,
    )

    team_level: Optional[str] = Field(
        default=None,
        max_length=50,
    )

    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
    )


# ---------------------------------------------------------
# REFEREE ASSIGNMENT
# ---------------------------------------------------------

class RefereeAssignment(BaseModel):
    referee_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
    )

    official_role: str = Field(
        default="Referee",
        max_length=50,
    )


# ---------------------------------------------------------
# APPOINTMENT RESPONSE
# ---------------------------------------------------------

class AppointmentResponse(BaseModel):
    appointment_id: str
    home_team_id: str
    home_team: str

    away_team_id: str
    away_team: str

    match_title: str
    match_date: date
    match_time: time

    venue: str

    competition: Optional[str] = None
    competition_type: Optional[str] = None
    season: Optional[str] = None
    team_level: Optional[str] = None
    notes: Optional[str] = None

    referee_id: Optional[str] = None
    referee_name: Optional[str] = None
    referee_email: Optional[str] = None
    official_role: Optional[str] = None

    status: str
    created_by_uid: str
