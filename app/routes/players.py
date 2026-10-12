"""
Player Registration Routes

Team administrators use these endpoints to manage players
belonging to their own team.

Security model:

Authenticated Firebase user
        ↓
Active team membership
        ↓
team_admin
        ↓
Can manage players for that team only
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.schemas.player_schema import (
    PlayerCreate,
    PlayerResponse,
    PlayerUpdate,
)

from app.services.firestore_service import get_firestore_client

from app.services.team_access_service import (
    require_team_manager,
    require_team_staff,
)

from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/api/teams",
    tags=["Players"],
)


def get_db():
    """
    Return Firestore client.
    """
    return get_firestore_client()


def build_player_response(
    player_id: str,
    data: dict,
) -> PlayerResponse:
    """
    Convert Firestore player data into the public API model.
    """

    return PlayerResponse(
        player_id=player_id,
        team_id=data["teamId"],
        first_name=data["firstName"],
        middle_name=data.get("middleName", ""),
        last_name=data["lastName"],
        date_of_birth=data["dateOfBirth"],
        gender=data.get("gender"),
        position=data.get("position"),
        jersey_number=data.get("jerseyNumber"),
        photo_url=data.get("photoUrl"),
        status=data.get("status", "active"),
        registration_status=data.get(
            "registrationStatus",
            "registered",
        ),
        created_at=data.get("createdAt"),
        updated_at=data.get("updatedAt"),
    )


@router.post(
    "/{team_id}/players",
    response_model=PlayerResponse,
)
def register_player(
    team_id: str,
    payload: PlayerCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Register a new player for a team.

    Only an active team administrator can perform this action.
    """

    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    # Verify that the authenticated user administers
    # this specific team.
    require_team_manager(uid, team_id)

    db = get_db()

    # Prevent duplicate jersey numbers within the team.
    if payload.jersey_number is not None:

        existing = (
            db.collection("players")
            .where("teamId", "==", team_id)
            .where(
                "jerseyNumber",
                "==",
                payload.jersey_number,
            )
            .where(
                "status",
                "==",
                "active",
            )
            .limit(1)
            .stream()
        )

        for player in existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This jersey number is already "
                    "assigned to an active player"
                ),
            )

    player_id = uuid4().hex

    now = datetime.now(timezone.utc)

    player_data = {
        "teamId": team_id,

        "firstName": payload.first_name,
        "middleName": payload.middle_name or "",
        "lastName": payload.last_name,

        "dateOfBirth": payload.date_of_birth,

        "gender": payload.gender,
        "position": payload.position,
        "jerseyNumber": payload.jersey_number,

        # Photo will be added through the upload endpoint.
        "photoUrl": None,

        "status": "active",
        "registrationStatus": "registered",

        "createdAt": now,
        "updatedAt": now,

        "createdBy": uid,
        "updatedBy": uid,
    }

    (
        db.collection("players")
        .document(player_id)
        .set(player_data)
    )

    return build_player_response(
        player_id,
        player_data,
    )


@router.get(
    "/{team_id}/players",
    response_model=list[PlayerResponse],
)
def list_team_players(
    team_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Return players registered to a team.

    Currently only team administrators can access the
    team's complete player register.
    """

    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    require_team_manager(uid, team_id)

    db = get_db()

    documents = (
        db.collection("players")
        .where("teamId", "==", team_id)
        .stream()
    )

    players = []

    for document in documents:
        players.append(
            build_player_response(
                document.id,
                document.to_dict(),
            )
        )

    return players


@router.patch(
    "/{team_id}/players/{player_id}",
    response_model=PlayerResponse,
)
def update_player(
    team_id: str,
    player_id: str,
    payload: PlayerUpdate,
    current_user: dict = Depends(get_current_user),
):
    """
    Update a player belonging to the specified team.
    """

    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    require_team_manager(uid, team_id)

    db = get_db()

    player_ref = (
        db.collection("players")
        .document(player_id)
    )

    snapshot = player_ref.get()

    if not snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found",
        )

    player = snapshot.to_dict()

    # Prevent a team administrator from modifying
    # another team's player.
    if player.get("teamId") != team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This player does not belong to your team",
        )

    updates = {}

    if payload.first_name is not None:
        updates["firstName"] = payload.first_name

    if payload.middle_name is not None:
        updates["middleName"] = payload.middle_name

    if payload.last_name is not None:
        updates["lastName"] = payload.last_name

    if payload.date_of_birth is not None:
        updates["dateOfBirth"] = payload.date_of_birth

    if payload.gender is not None:
        updates["gender"] = payload.gender

    if payload.position is not None:
        updates["position"] = payload.position

    if payload.jersey_number is not None:
        updates["jerseyNumber"] = payload.jersey_number

    if payload.status is not None:
        updates["status"] = payload.status

    updates["updatedAt"] = datetime.now(timezone.utc)
    updates["updatedBy"] = uid

    player_ref.update(updates)

    updated_player = {
        **player,
        **updates,
    }

    return build_player_response(
        player_id,
        updated_player,
    )