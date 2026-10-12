from datetime import datetime, timezone
from google.cloud.firestore import Client

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.match_schema import (
    MatchCreate,
    MatchRefereeAssign,
    MatchResponse,
    MatchUpdate,
)
from app.services.firestore_service import get_firestore_client
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/api/clubs/{club_id}/matches",
    tags=["Matches"],
)


# ---------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------

VALID_MATCH_STATUSES = {
    "scheduled",
    "in_progress",
    "completed",
    "cancelled",
}

MANAGEMENT_ROLES = {
    "owner",
    "admin",
}


# ---------------------------------------------------------
# AUTHENTICATION HELPER
# ---------------------------------------------------------

def get_authenticated_uid(current_user: dict) -> str:
    """
    Extract the Firebase UID from the verified Firebase
    authentication token.
    """
    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user UID not found",
        )

    return uid


# ---------------------------------------------------------
# CLUB MEMBERSHIP
# ---------------------------------------------------------

def get_club_member(club_id: str, uid: str, db: Client):
    """
    Get the user's membership document for this club.
    """
    member_ref = (
        db.collection("clubs")
        .document(club_id)
        .collection("members")
        .document(uid)
    )

    member_doc = member_ref.get()

    if not member_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this club",
        )

    member = member_doc.to_dict()

    if member.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your club membership is not active",
        )

    return member


# ---------------------------------------------------------
# MANAGEMENT ACCESS
# ---------------------------------------------------------

def require_match_management_access(
    club_id: str,
    uid: str,
    db: Client,
):
    """
    Only club owners and administrators can currently
    create, edit, cancel or assign referees to matches.
    """
    member = get_club_member(club_id, uid, db)

    if member.get("role") not in MANAGEMENT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only club owners and administrators can manage matches",
        )

    return member


# ---------------------------------------------------------
# TEAM LOOKUP
# ---------------------------------------------------------

def get_team(club_id: str, team_id: str, db: Client):
    """
    Retrieve a team belonging to this club.
    """
    team_ref = (
        db.collection("clubs")
        .document(club_id)
        .collection("teams")
        .document(team_id)
    )

    team_doc = team_ref.get()

    if not team_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    team = team_doc.to_dict()

    if team.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected team is not active",
        )

    return team


# ---------------------------------------------------------
# MATCH RESPONSE BUILDER
# ---------------------------------------------------------

def build_match_response(match_id: str, data: dict) -> MatchResponse:
    """
    Convert the Firestore match document into the API
    response structure expected by the frontend.
    """
    return MatchResponse(
        match_id=match_id,
        club_id=data["club_id"],
        home_team_id=data["home_team_id"],
        home_team_name=data["home_team_name"],
        away_team_id=data.get("away_team_id"),
        away_team_name=data["away_team_name"],
        away_club_id=data.get("away_club_id"),
        match_date=data["match_date"],
        match_time=data["match_time"],
        venue=data["venue"],
        competition=data.get("competition"),
        season=data.get("season"),
        status=data.get("status", "scheduled"),
        referee_uid=data.get("referee_uid"),
        created_by_uid=data["created_by_uid"],
    )


# ---------------------------------------------------------
# CREATE MATCH
# ---------------------------------------------------------

@router.post(
    "",
    response_model=MatchResponse,
)
def create_match(
    club_id: str,
    payload: MatchCreate,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_firestore_client),
):
    """
    Create a new fixture for a club.
    """
    uid = get_authenticated_uid(current_user)

    require_match_management_access(
        club_id,
        uid,
        db,
    )

    home_team = get_team(
        club_id,
        payload.home_team_id,
        db,
    )

    if payload.away_team_id:
        if not payload.away_club_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="away_club_id is required when away_team_id is supplied",
            )

        away_team = get_team(
            payload.away_club_id,
            payload.away_team_id,
            db,
        )

        if (
            payload.away_club_id == club_id
            and payload.away_team_id == payload.home_team_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Home and away teams cannot be the same team",
            )

        away_team_name = away_team.get(
            "name",
            payload.away_team_name,
        )
    else:
        away_team_name = payload.away_team_name

    match_ref = (
        db.collection("clubs")
        .document(club_id)
        .collection("matches")
        .document()
    )

    now = datetime.now(timezone.utc)

    match_data = {
        "match_id": match_ref.id,
        "club_id": club_id,
        "home_team_id": payload.home_team_id,
        "home_team_name": home_team.get("name"),
        "away_team_id": payload.away_team_id,
        "away_team_name": away_team_name,
        "away_club_id": payload.away_club_id,
        "match_date": payload.match_date.isoformat(),
        "match_time": payload.match_time.isoformat(),
        "venue": payload.venue,
        "competition": payload.competition,
        "season": payload.season,
        "status": "scheduled",
        "referee_uid": None,
        "created_by_uid": uid,
        "created_at": now,
        "updated_at": now,
    }

    match_ref.set(match_data)

    return build_match_response(
        match_ref.id,
        match_data,
    )


# ---------------------------------------------------------
# LIST CLUB MATCHES
# ---------------------------------------------------------

@router.get(
    "",
    response_model=list[MatchResponse],
)
def list_matches(
    club_id: str,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_firestore_client),
):
    """
    Return all active/scheduled matches for a club.
    """
    uid = get_authenticated_uid(current_user)

    get_club_member(
        club_id,
        uid,
        db,
    )

    matches_ref = (
        db.collection("clubs")
        .document(club_id)
        .collection("matches")
    )

    docs = matches_ref.stream()

    matches = []

    for doc in docs:
        data = doc.to_dict()

        data["match_date"] = datetime.fromisoformat(
            data["match_date"]
        ).date()

        data["match_time"] = datetime.fromisoformat(
            f"2000-01-01T{data['match_time']}"
        ).time()

        matches.append(
            build_match_response(
                doc.id,
                data,
            )
        )

    matches.sort(
        key=lambda match: (
            match.match_date,
            match.match_time,
        )
    )

    return matches


# ---------------------------------------------------------
# GET ONE MATCH
# ---------------------------------------------------------

@router.get(
    "/{match_id}",
    response_model=MatchResponse,
)
def get_match(
    club_id: str,
    match_id: str,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_firestore_client),
):
    """
    Retrieve one fixture.
    """
    uid = get_authenticated_uid(current_user)

    get_club_member(
        club_id,
        uid,
        db,
    )

    match_ref = (
        db.collection("clubs")
        .document(club_id)
        .collection("matches")
        .document(match_id)
    )

    match_doc = match_ref.get()

    if not match_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    data = match_doc.to_dict()

    data["match_date"] = datetime.fromisoformat(
        data["match_date"]
    ).date()

    data["match_time"] = datetime.fromisoformat(
        f"2000-01-01T{data['match_time']}"
    ).time()

    return build_match_response(
        match_doc.id,
        data,
    )


# ---------------------------------------------------------
# UPDATE MATCH
# ---------------------------------------------------------

@router.patch(
    "/{match_id}",
    response_model=MatchResponse,
)
def update_match(
    club_id: str,
    match_id: str,
    payload: MatchUpdate,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_firestore_client),
):
    """
    Update fixture information.
    """
    uid = get_authenticated_uid(current_user)

    require_match_management_access(
        club_id,
        uid,
        db,
    )

    match_ref = (
        db.collection("clubs")
        .document(club_id)
        .collection("matches")
        .document(match_id)
    )

    match_doc = match_ref.get()

    if not match_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    data = match_doc.to_dict()

    if data.get("status") != "scheduled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only scheduled matches can be edited",
        )

    updates = {}

    if payload.home_team_id is not None:
        home_team = get_team(
            club_id,
            payload.home_team_id,
            db,
        )

        updates["home_team_id"] = payload.home_team_id
        updates["home_team_name"] = home_team.get("name")

    if payload.away_team_id is not None:
        if not payload.away_club_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="away_club_id is required when away_team_id is supplied",
            )

        away_team = get_team(
            payload.away_club_id,
            payload.away_team_id,
            db,
        )

        updates["away_team_id"] = payload.away_team_id
        updates["away_club_id"] = payload.away_club_id
        updates["away_team_name"] = away_team.get(
            "name",
            payload.away_team_name or data["away_team_name"],
        )

    elif payload.away_team_name is not None:
        updates["away_team_name"] = payload.away_team_name
        updates["away_team_id"] = None
        updates["away_club_id"] = None

    if payload.match_date is not None:
        updates["match_date"] = payload.match_date.isoformat()

    if payload.match_time is not None:
        updates["match_time"] = payload.match_time.isoformat()

    if payload.venue is not None:
        updates["venue"] = payload.venue

    if payload.competition is not None:
        updates["competition"] = payload.competition

    if payload.season is not None:
        updates["season"] = payload.season

    updates["updated_at"] = datetime.now(timezone.utc)

    match_ref.update(updates)

    updated_doc = match_ref.get()
    updated_data = updated_doc.to_dict()

    updated_data["match_date"] = datetime.fromisoformat(
        updated_data["match_date"]
    ).date()

    updated_data["match_time"] = datetime.fromisoformat(
        f"2000-01-01T{updated_data['match_time']}"
    ).time()

    return build_match_response(
        updated_doc.id,
        updated_data,
    )


# ---------------------------------------------------------
# CANCEL MATCH
# ---------------------------------------------------------

@router.patch(
    "/{match_id}/cancel",
    response_model=MatchResponse,
)
def cancel_match(
    club_id: str,
    match_id: str,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_firestore_client),
):
    """
    Cancel a fixture without deleting its historical record.
    """
    uid = get_authenticated_uid(current_user)

    require_match_management_access(
        club_id,
        uid,
        db,
    )

    match_ref = (
        db.collection("clubs")
        .document(club_id)
        .collection("matches")
        .document(match_id)
    )

    match_doc = match_ref.get()

    if not match_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    data = match_doc.to_dict()

    if data.get("status") == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A completed match cannot be cancelled",
        )

    match_ref.update({
        "status": "cancelled",
        "updated_at": datetime.now(timezone.utc),
    })

    data["status"] = "cancelled"

    data["match_date"] = datetime.fromisoformat(
        data["match_date"]
    ).date()

    data["match_time"] = datetime.fromisoformat(
        f"2000-01-01T{data['match_time']}"
    ).time()

    return build_match_response(
        match_doc.id,
        data,
    )


# ---------------------------------------------------------
# ASSIGN REFEREE
# ---------------------------------------------------------

@router.post(
    "/{match_id}/referee",
    response_model=MatchResponse,
)
def assign_referee(
    club_id: str,
    match_id: str,
    payload: MatchRefereeAssign,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_firestore_client),
):
    """
    Assign a referee to a match.
    """
    uid = get_authenticated_uid(current_user)

    require_match_management_access(
        club_id,
        uid,
        db,
    )

    match_ref = (
        db.collection("clubs")
        .document(club_id)
        .collection("matches")
        .document(match_id)
    )

    match_doc = match_ref.get()

    if not match_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    data = match_doc.to_dict()

    if data.get("status") == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign a referee to a cancelled match",
        )

    referee_member_ref = (
        db.collection("clubs")
        .document(club_id)
        .collection("members")
        .document(payload.referee_uid)
    )

    referee_member_doc = referee_member_ref.get()

    if not referee_member_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected referee is not a member of this club",
        )

    referee_member = referee_member_doc.to_dict()

    if referee_member.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected referee is not active",
        )

    if referee_member.get("role") != "referee":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected club member is not registered as a referee",
        )

    match_ref.update({
        "referee_uid": payload.referee_uid,
        "updated_at": datetime.now(timezone.utc),
    })

    data["referee_uid"] = payload.referee_uid

    data["match_date"] = datetime.fromisoformat(
        data["match_date"]
    ).date()

    data["match_time"] = datetime.fromisoformat(
        f"2000-01-01T{data['match_time']}"
    ).time()

    return build_match_response(
        match_doc.id,
        data,
    )