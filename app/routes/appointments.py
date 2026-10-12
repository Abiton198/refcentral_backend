"""
Appointment Routes

Fixtures are created by executives.

A fixture connects:

Home Team
Away Team
Referee
Date
Time
Venue
Competition

Access:

Executive
    → create / manage

Team Manager / Coach
    → view fixtures involving their team

Referee
    → view fixtures assigned to them

Later:

Appointment
    ↓
Squads
    ↓
Teamsheets
    ↓
Matchday verification
"""


from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.schemas.appointment_schema import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentUpdate,
    RefereeAssignment,
)

from app.services.firestore_service import (
    get_firestore_client,
)

from app.services.appointment_access_service import (
    get_appointment_document,
    get_user_document,
    require_appointment_view_access,
    require_executive,
)

from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/api/appointments",
    tags=["Appointments"],
)


def get_db():
    """
    Return Firestore client.
    """
    return get_firestore_client()


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def get_team(
    team_id: str,
):
    """
    Retrieve a team by ID.
    """

    db = get_db()

    snapshot = (
        db.collection("teams")
        .document(team_id)
        .get()
    )

    if not snapshot.exists:
        return None

    return snapshot.to_dict()


def build_appointment_response(
    appointment_id: str,
    data: dict,
) -> AppointmentResponse:
    """
    Convert Firestore appointment data into the API model.
    """

    return AppointmentResponse(
        appointment_id=appointment_id,

        home_team_id=data["homeTeamId"],
        home_team=data["homeTeam"],

        away_team_id=data["awayTeamId"],
        away_team=data["awayTeam"],

        match_title=data["matchTitle"],

        match_date=data["matchDate"],
        match_time=data["matchTime"],

        venue=data["venue"],

        competition=data.get(
            "competition"
        ),

        competition_type=data.get(
            "competitionType"
        ),

        season=data.get(
            "season"
        ),

        team_level=data.get(
            "teamLevel"
        ),

        notes=data.get(
            "notes"
        ),

        referee_id=data.get(
            "refereeId"
        ),

        referee_name=data.get(
            "refereeName"
        ),

        referee_email=data.get(
            "refereeEmail"
        ),

        official_role=data.get(
            "officialRole"
        ),

        status=data.get(
            "status",
            "scheduled",
        ),

        created_by_uid=data.get(
            "createdByUid",
            "",
        ),
    )


# ---------------------------------------------------------
# Create appointment
# ---------------------------------------------------------

@router.post(
    "",
    response_model=AppointmentResponse,
)
def create_appointment(
    payload: AppointmentCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new fixture.

    Only executives can create fixtures.
    """

    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    require_executive(uid)

    # -----------------------------------------------------
    # Verify home team
    # -----------------------------------------------------

    home_team = get_team(
        payload.home_team_id
    )

    if not home_team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Home team not found",
        )

    # -----------------------------------------------------
    # Verify away team
    # -----------------------------------------------------

    away_team = get_team(
        payload.away_team_id
    )

    if not away_team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Away team not found",
        )

    # A team cannot play itself.
    if (
        payload.home_team_id
        == payload.away_team_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Home and away teams must be different",
        )

    # -----------------------------------------------------
    # Generate appointment
    # -----------------------------------------------------

    appointment_id = uuid4().hex

    now = datetime.now(timezone.utc)

    match_date = (
        payload.match_date.isoformat()
    )

    match_time = (
        payload.match_time.strftime("%H:%M")
    )

    match_title = (
        f"{home_team.get('name', 'Home Team')} "
        f"vs "
        f"{away_team.get('name', 'Away Team')}"
    )

    appointment_data = {
        "homeTeamId": payload.home_team_id,
        "homeTeam": home_team.get(
            "name",
            "",
        ),

        "awayTeamId": payload.away_team_id,
        "awayTeam": away_team.get(
            "name",
            "",
        ),

        "matchTitle": match_title,

        "matchDate": match_date,
        "date": match_date,

        "matchTime": match_time,
        "time": match_time,

        "venue": payload.venue,

        "competition": payload.competition,
        "competitionType": payload.competition_type,

        "season": payload.season,

        "teamLevel": payload.team_level,

        "notes": payload.notes or "",

        "refereeId": None,
        "refereeName": None,
        "refereeEmail": None,
        "officialRole": None,

        "status": "scheduled",

        "createdByUid": uid,
        "createdAt": now,
        "updatedAt": now,

        "auditTrail": [
            {
                "action": "created",
                "byUid": uid,
                "timestamp": now,
            }
        ],
    }

    db = get_db()

    (
        db.collection("appointments")
        .document(appointment_id)
        .set(appointment_data)
    )

    return build_appointment_response(
        appointment_id,
        appointment_data,
    )


# ---------------------------------------------------------
# Get appointment
# ---------------------------------------------------------

@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
)
def get_appointment(
    appointment_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve a single appointment.

    Access is determined by the appointment access service.
    """

    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    appointment = get_appointment_document(
        appointment_id
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    require_appointment_view_access(
        uid,
        appointment,
    )

    return build_appointment_response(
        appointment_id,
        appointment,
    )


# ---------------------------------------------------------
# List appointments for current user
# ---------------------------------------------------------

@router.get(
    "",
    response_model=list[AppointmentResponse],
)
def list_my_appointments(
    current_user: dict = Depends(get_current_user),
):
    """
    Return fixtures relevant to the authenticated user.

    Executive:
        all fixtures

    Team Manager / Coach:
        fixtures involving their team

    Referee:
        fixtures assigned to them
    """

    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    db = get_db()

    # -----------------------------------------------------
    # Executive
    # -----------------------------------------------------

    if get_user_document(uid) and (
        str(
            get_user_document(uid).get(
                "role",
                get_user_document(uid).get(
                    "userRole",
                    "",
                ),
            )
        ).lower()
        == "executive"
    ):
        documents = (
            db.collection("appointments")
            .stream()
        )

        appointments = []

        for document in documents:
            appointments.append(
                build_appointment_response(
                    document.id,
                    document.to_dict(),
                )
            )

        return appointments

    # -----------------------------------------------------
    # Find teams where this user is a Team Manager or Coach.
    # -----------------------------------------------------

    # Query Team Manager and Coach memberships separately.
    # This keeps the supported roles explicit and avoids relying on a
    # Firestore "in" query or requiring an additional composite index.
    manager_memberships = (
        db.collection("team_memberships")
        .where("userId", "==", uid)
        .where("role", "==", "team_manager")
        .where("status", "==", "active")
        .stream()
    )

    coach_memberships = (
        db.collection("team_memberships")
        .where("userId", "==", uid)
        .where("role", "==", "coach")
        .where("status", "==", "active")
        .stream()
    )

    team_ids = set()

    for membership in manager_memberships:
        team_id = membership.to_dict().get("teamId")
        if team_id:
            team_ids.add(team_id)

    for membership in coach_memberships:
        team_id = membership.to_dict().get("teamId")
        if team_id:
            team_ids.add(team_id)

    # -----------------------------------------------------
    # Collect appointments without duplicates.
    # -----------------------------------------------------

    appointment_documents = {}

    # Team Manager / Coach fixtures.
    for team_id in team_ids:

        home_documents = (
            db.collection("appointments")
            .where(
                "homeTeamId",
                "==",
                team_id,
            )
            .stream()
        )

        away_documents = (
            db.collection("appointments")
            .where(
                "awayTeamId",
                "==",
                team_id,
            )
            .stream()
        )

        for document in home_documents:
            appointment_documents[
                document.id
            ] = document

        for document in away_documents:
            appointment_documents[
                document.id
            ] = document

    # Referee fixtures.
    referee_documents = (
        db.collection("appointments")
        .where(
            "refereeId",
            "==",
            uid,
        )
        .stream()
    )

    for document in referee_documents:
        appointment_documents[
            document.id
        ] = document

    results = []

    for document in appointment_documents.values():

        results.append(
            build_appointment_response(
                document.id,
                document.to_dict(),
            )
        )

    return results


# ---------------------------------------------------------
# Update appointment
# ---------------------------------------------------------

@router.patch(
    "/{appointment_id}",
    response_model=AppointmentResponse,
)
def update_appointment(
    appointment_id: str,
    payload: AppointmentUpdate,
    current_user: dict = Depends(get_current_user),
):
    """
    Update fixture details.

    Only executives can change the fixture.
    """

    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    require_executive(uid)

    db = get_db()

    appointment_ref = (
        db.collection("appointments")
        .document(appointment_id)
    )

    snapshot = appointment_ref.get()

    if not snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    appointment = snapshot.to_dict()

    updates = {}

    if payload.match_date is not None:

        match_date = (
            payload.match_date.isoformat()
        )

        updates["matchDate"] = match_date
        updates["date"] = match_date

    if payload.match_time is not None:

        match_time = (
            payload.match_time.strftime("%H:%M")
        )

        updates["matchTime"] = match_time
        updates["time"] = match_time

    if payload.venue is not None:
        updates["venue"] = payload.venue

    if payload.competition is not None:
        updates["competition"] = (
            payload.competition
        )

    if payload.competition_type is not None:
        updates["competitionType"] = (
            payload.competition_type
        )

    if payload.season is not None:
        updates["season"] = payload.season

    if payload.team_level is not None:
        updates["teamLevel"] = payload.team_level

    if payload.notes is not None:
        updates["notes"] = payload.notes

    updates["updatedAt"] = (
        datetime.now(timezone.utc)
    )

    appointment_ref.update(updates)

    updated = {
        **appointment,
        **updates,
    }

    return build_appointment_response(
        appointment_id,
        updated,
    )


# ---------------------------------------------------------
# Assign referee
# ---------------------------------------------------------
@router.post(
    "/{appointment_id}/referee",
    response_model=AppointmentResponse,
)
def assign_referee(
    appointment_id: str,
    payload: RefereeAssignment,
    current_user: dict = Depends(get_current_user),
    db: Any = Depends(get_firestore_client),
):
    """
    Assign a referee to a fixture.

    Only executives can assign officials.
    """

    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    require_executive(uid)

    # 1. Fetch existing appointment
    appointment_ref = db.collection("appointments").document(appointment_id)
    appointment_snapshot = appointment_ref.get()

    if not appointment_snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    appointment = appointment_snapshot.to_dict() or {}

    # 2. Verify referee exists (Check 'users' then 'referees' collection)
    referee_user = get_user_document(payload.referee_id)

    referee_name = None
    referee_email = None

    if referee_user:
        referee_name = (
            referee_user.get("displayName")
            or referee_user.get("name")
            or referee_user.get("fullName")
        )
        referee_email = referee_user.get("email")

    # If not found in users, check referees collection
    if not referee_user:
        referee_snapshot = (
            db.collection("referees")
            .document(payload.referee_id)
            .get()
        )

        if not referee_snapshot.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referee not found",
            )

        referee = referee_snapshot.to_dict() or {}

        referee_name = (
            referee.get("displayName")
            or referee.get("name")
            or referee.get("fullName")
        )
        referee_email = referee.get("email")

    # 3. Construct update payload and audit entry
    now = datetime.now(timezone.utc)

    audit_trail = list(appointment.get("auditTrail", []))
    audit_trail.append(
        {
            "action": "referee_assigned",
            "byUid": uid,
            "refereeId": payload.referee_id,
            "officialRole": payload.official_role,
            "timestamp": now,
        }
    )

    updates = {
        "refereeId": payload.referee_id,
        "refereeName": referee_name,
        "refereeEmail": referee_email,
        "officialRole": payload.official_role,
        "updatedAt": now,
        "auditTrail": audit_trail,
    }

    # 4. Safe write using set(..., merge=True) instead of update()
    appointment_ref.set(updates, merge=True)

    # 5. Build merged dict for response builder
    updated = {
        **appointment,
        **updates,
    }

    return build_appointment_response(
        appointment_id,
        updated,
    )
