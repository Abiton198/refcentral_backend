"""
Team Membership Routes

Executives use these routes to assign Team Managers
and Coaches to teams.

Users cannot assign themselves to teams.

Supported roles:

    team_manager
    coach
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.team_membership_schema import (
    TeamMembershipCreate,
    TeamMembershipResponse,
)

from app.services.firestore_service import get_firestore_client

from app.services.appointment_access_service import (
    require_executive,
)

from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/api/teams",
    tags=["Team Memberships"],
)


# ---------------------------------------------------------
# CREATE MEMBERSHIP
# ---------------------------------------------------------

@router.post(
    "/{team_id}/memberships",
    response_model=TeamMembershipResponse,
)
def create_team_membership(
    team_id: str,
    payload: TeamMembershipCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Assign a user to a team.

    ONLY an Executive may perform this operation.
    """

    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=401,
            detail="Authenticated user UID is missing",
        )

    # Executive-only operation.
    require_executive(uid)

    db = get_firestore_client()

    # -----------------------------------------------------
    # VERIFY TEAM
    # -----------------------------------------------------

    team_ref = (
        db.collection("teams")
        .document(team_id)
    )

    team_snapshot = team_ref.get()

    if not team_snapshot.exists:
        raise HTTPException(
            status_code=404,
            detail="Team not found",
        )

    # -----------------------------------------------------
    # VERIFY USER
    # -----------------------------------------------------

    user_ref = (
        db.collection("users")
        .document(payload.user_id)
    )

    user_snapshot = user_ref.get()

    if not user_snapshot.exists:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    user_data = user_snapshot.to_dict()

    # -----------------------------------------------------
    # VERIFY USER ROLE
    # -----------------------------------------------------

    requested_role = (
        payload.role
        .strip()
        .lower()
    )

    if requested_role not in {
        "team_manager",
        "coach",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid team membership role. "
                "Use 'team_manager' or 'coach'."
            ),
        )

    # -----------------------------------------------------
    # USER MUST HAVE THE CORRESPONDING GLOBAL ROLE
    # -----------------------------------------------------

    global_role = str(
        user_data.get("role", "")
    ).strip().lower()

    if global_role != requested_role:
        raise HTTPException(
            status_code=400,
            detail=(
                f"User account role is '{global_role}', "
                f"but this membership requires "
                f"'{requested_role}'."
            ),
        )

    # -----------------------------------------------------
    # PREVENT DUPLICATE ACTIVE MEMBERSHIP
    # -----------------------------------------------------

    existing = (
        db.collection("team_memberships")
        .where("userId", "==", payload.user_id)
        .where("teamId", "==", team_id)
        .where("status", "==", "active")
        .limit(10)
        .stream()
    )

    for membership in existing:
        existing_data = membership.to_dict()

        existing_role = str(
            existing_data.get("role", "")
        ).strip().lower()

        if existing_role == requested_role:
            raise HTTPException(
                status_code=409,
                detail=(
                    "This user already has an active "
                    f"{requested_role} membership for this team."
                ),
            )

        # One active team role per user/team.
        raise HTTPException(
            status_code=409,
            detail=(
                "This user already has an active membership "
                "for this team."
            ),
        )

    # -----------------------------------------------------
    # CREATE MEMBERSHIP
    # -----------------------------------------------------

    now = datetime.now(timezone.utc)

    membership_ref = (
        db.collection("team_memberships")
        .document()
    )

    membership_data = {
        "teamId": team_id,
        "userId": payload.user_id,
        "role": requested_role,
        "status": "active",
        "createdAt": now,
        "createdBy": uid,
    }

    membership_ref.set(
        membership_data
    )

    return TeamMembershipResponse(
        membership_id=membership_ref.id,
        team_id=team_id,
        user_id=payload.user_id,
        role=requested_role,
        status="active",
        created_at=now,
        created_by=uid,
    )