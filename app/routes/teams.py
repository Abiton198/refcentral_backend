"""
Team Routes

Team management for the new RefCentral architecture.

Architecture:

                    Executive
                       |
                       | creates/manages
                       v
                     Teams
                       |
                       | team_memberships
                       v
                Team Administrators
                       |
                       v
                    Players

Important security rule:

The backend NEVER trusts a team ID supplied by the frontend
to determine what a user is allowed to do.

Permissions are checked using:

Firebase UID
     ↓
team_memberships
     ↓
team ID
     ↓
role
"""


from datetime import datetime, timezone
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from pydantic import BaseModel, Field

from app.services.firestore_service import get_firestore_client
from app.services.appointment_access_service import (
    require_executive,
)

from app.utils.auth import get_current_user


# ---------------------------------------------------------
# Router
# ---------------------------------------------------------

router = APIRouter(
    prefix="/api/teams",
    tags=["Teams"],
)


# ---------------------------------------------------------
# Firestore
# ---------------------------------------------------------

def get_db():
    """
    Return the Firestore database client.
    """
    return get_firestore_client()


# ---------------------------------------------------------
# Schemas
# ---------------------------------------------------------

class TeamCreate(BaseModel):
    """
    Data required to create a new team.
    """

    name: str = Field(
        ...,
        min_length=2,
        max_length=150,
    )

    home_ground: str | None = Field(
        default=None,
        max_length=150,
    )

    league: str | None = Field(
        default=None,
        max_length=150,
    )


class TeamUpdate(BaseModel):
    """
    Fields that can be changed on an existing team.
    """

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    home_ground: str | None = Field(
        default=None,
        max_length=150,
    )

    league: str | None = Field(
        default=None,
        max_length=150,
    )

    status: str | None = Field(
        default=None,
        max_length=30,
    )


class TeamResponse(BaseModel):
    """
    Public representation of a team.
    """

    team_id: str
    name: str
    home_ground: str | None = None
    league: str | None = None
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------
# Helper
# ---------------------------------------------------------

def build_team_response(
    team_id: str,
    data: dict,
) -> TeamResponse:
    """
    Convert Firestore team data into the API response model.
    """

    return TeamResponse(
        team_id=team_id,
        name=data.get("name", ""),
        home_ground=data.get("homeGround"),
        league=data.get("league"),
        status=data.get(
            "status",
            "active",
        ),
        created_at=data.get("createdAt"),
        updated_at=data.get("updatedAt"),
    )


# ---------------------------------------------------------
# Create team
# ---------------------------------------------------------

@router.post(
    "",
    response_model=TeamResponse,
)
def create_team(
    payload: TeamCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new rugby team.

    Only executives can create teams.
    """

    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    # Only executives can create teams.
    require_executive(uid)

    db = get_db()

    # Generate a unique Firestore document ID.
    team_id = uuid4().hex

    now = datetime.now(timezone.utc)

    team_data = {
        "name": payload.name.strip(),
        "homeGround": (
            payload.home_ground.strip()
            if payload.home_ground
            else None
        ),
        "league": (
            payload.league.strip()
            if payload.league
            else None
        ),
        "status": "active",
        "createdAt": now,
        "updatedAt": now,
        "createdBy": uid,
    }

    (
        db.collection("teams")
        .document(team_id)
        .set(team_data)
    )

    return build_team_response(
        team_id,
        team_data,
    )


# ---------------------------------------------------------
# List teams
# ---------------------------------------------------------

@router.get(
    "",
    response_model=list[TeamResponse],
)
def list_teams(
    current_user: dict = Depends(get_current_user),
):
    """
    Return all active teams.

    For now this endpoint is available to authenticated
    RefCentral users.

    We can later restrict this further depending on the
    user's role.
    """

    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    db = get_db()

    documents = (
        db.collection("teams")
        .where("status", "==", "active")
        .stream()
    )

    teams = []

    for document in documents:

        teams.append(
            build_team_response(
                document.id,
                document.to_dict(),
            )
        )

    return teams


# ---------------------------------------------------------
# Get one team
# ---------------------------------------------------------

@router.get(
    "/{team_id}",
    response_model=TeamResponse,
)
def get_team(
    team_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve one team.
    """

    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    db = get_db()

    snapshot = (
        db.collection("teams")
        .document(team_id)
        .get()
    )

    if not snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    return build_team_response(
        team_id,
        snapshot.to_dict(),
    )


# ---------------------------------------------------------
# Update team
# ---------------------------------------------------------

@router.patch(
    "/{team_id}",
    response_model=TeamResponse,
)
def update_team(
    team_id: str,
    payload: TeamUpdate,
    current_user: dict = Depends(get_current_user),
):
    """
    Update an existing team.

    Only executives can change team information.
    """

    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    require_executive(uid)

    db = get_db()

    team_ref = (
        db.collection("teams")
        .document(team_id)
    )

    snapshot = team_ref.get()

    if not snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    existing_team = snapshot.to_dict()

    updates = {}

    if payload.name is not None:
        updates["name"] = payload.name.strip()

    if payload.home_ground is not None:
        updates["homeGround"] = (
            payload.home_ground.strip()
        )

    if payload.league is not None:
        updates["league"] = (
            payload.league.strip()
        )

    if payload.status is not None:
        updates["status"] = (
            payload.status.strip().lower()
        )

    updates["updatedAt"] = (
        datetime.now(timezone.utc)
    )

    team_ref.update(updates)

    updated_team = {
        **existing_team,
        **updates,
    }

    return build_team_response(
        team_id,
        updated_team,
    )