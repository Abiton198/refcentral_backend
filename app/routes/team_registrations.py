
"""
Team Registration Routes

Allows authenticated users to request registration of a team.

Security:
- Firebase identity is verified by get_current_user.
- Existing global roles cannot be silently replaced.
- Registrations and teams remain pending until Executive approval.
- Only an Executive can create the active team membership.
"""

import re
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.firestore_service import get_firestore_client
from app.services.appointment_access_service import require_executive
from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/api/team-registrations",
    tags=["Team Registrations"],
)


class TeamDetails(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    clubName: str = Field(min_length=2, max_length=150)
    teamType: str = Field(min_length=1, max_length=80)
    ageGroup: str = Field(min_length=1, max_length=80)
    division: str = Field(default="", max_length=150)
    homeGround: str = Field(min_length=1, max_length=150)
    city: str = Field(min_length=1, max_length=150)
    colours: str = Field(default="", max_length=100)


class ManagerDetails(BaseModel):
    displayName: str = Field(min_length=2, max_length=150)
    mobileNumber: str = Field(min_length=5, max_length=30)
    altContact: str = Field(default="", max_length=30)


class TeamRegistrationCreate(BaseModel):
    team: TeamDetails
    manager: ManagerDetails


def get_uid(current_user: dict) -> str:
    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=401,
            detail="Authenticated user UID is missing",
        )

    return uid


def slugify(value: str) -> str:
    return re.sub(
        r"-+",
        "-",
        re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-"),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def register_team(
    payload: TeamRegistrationCreate,
    current_user: dict = Depends(get_current_user),
):
    """Submit a team registration for Executive approval."""

    uid = get_uid(current_user)
    db = get_firestore_client()

    email = current_user.get("email")

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Your authenticated account has no email address",
        )

    user_ref = db.collection("users").document(uid)
    user_snapshot = user_ref.get()
    user_data = user_snapshot.to_dict() if user_snapshot.exists else {}

    existing_role = str(
        user_data.get("role") or user_data.get("userRole") or ""
    ).strip().lower()

    if existing_role and existing_role != "team_manager":
        raise HTTPException(
            status_code=409,
            detail=(
                f"This account already has the role '{existing_role}'. "
                "Contact an Executive if your role needs correction."
            ),
        )

    # Do not allow a second pending application from the same user.
    pending = (
        db.collection("team_registrations")
        .where("userId", "==", uid)
        .where("status", "==", "pending")
        .limit(1)
        .stream()
    )

    if next(iter(pending), None):
        raise HTTPException(
            status_code=409,
            detail="You already have a pending team registration",
        )

    team_name = payload.team.name.strip()
    club_name = payload.team.clubName.strip()
    age_group = payload.team.ageGroup.strip()

    # Use a unique document ID. Never trust a team ID from the browser.
    team_id = uuid4().hex
    registration_id = uuid4().hex
    now = datetime.now(timezone.utc)

    team_data = {
        "name": team_name,
        "nameLower": team_name.lower(),
        "clubName": club_name,
        "teamType": payload.team.teamType.strip(),
        "ageGroup": age_group,
        "division": payload.team.division.strip(),
        "league": payload.team.division.strip() or None,
        "homeGround": payload.team.homeGround.strip(),
        "city": payload.team.city.strip(),
        "colours": payload.team.colours.strip(),
        "status": "pending",
        "approved": False,
        "createdBy": uid,
        "createdAt": now,
        "updatedAt": now,
    }

    manager_data = {
        "uid": uid,
        "email": email,
        "displayName": payload.manager.displayName.strip(),
        "mobileNumber": payload.manager.mobileNumber.strip(),
        "altContact": payload.manager.altContact.strip(),
        "role": "team_manager",
        "status": "pending",
        "approved": False,
        "createdAt": now,
        "updatedAt": now,
    }

    registration_data = {
        "userId": uid,
        "teamId": team_id,
        "teamName": team_name,
        "role": "team_manager",
        "status": "pending",
        "createdAt": now,
        "updatedAt": now,
    }

    batch = db.batch()

    # Set the global role only when no role has previously been assigned.
    if not user_snapshot.exists:
        batch.set(user_ref, {
            "uid": uid,
            "email": email,
            "displayName": manager_data["displayName"],
            "role": "team_manager",
            "status": "pending",
            "createdAt": now,
            "updatedAt": now,
        })
    elif not existing_role:
        batch.update(user_ref, {
            "role": "team_manager",
            "status": "pending",
            "updatedAt": now,
        })

    batch.set(db.collection("teams").document(team_id), team_data)
    batch.set(
        db.collection("team_registrations").document(registration_id),
        registration_data,
    )

    # Keep contact details private rather than putting them on a public team.
    batch.set(
        db.collection("team_manager_profiles").document(uid),
        manager_data,
    )

    batch.commit()

    return {
        "success": True,
        "message": "Registration submitted for Executive approval",
        "registration_id": registration_id,
        "team_id": team_id,
        "status": "pending",
    }


@router.post("/{registration_id}/approve")
def approve_team_registration(
    registration_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Approve a registration and activate the manager membership."""

    executive_uid = get_uid(current_user)
    require_executive(executive_uid)

    db = get_firestore_client()

    registration_ref = (
        db.collection("team_registrations").document(registration_id)
    )
    registration_snapshot = registration_ref.get()

    if not registration_snapshot.exists:
        raise HTTPException(status_code=404, detail="Registration not found")

    registration = registration_snapshot.to_dict()

    if registration.get("status") != "pending":
        raise HTTPException(
            status_code=409,
            detail="This registration is no longer pending",
        )

    uid = registration.get("userId")
    team_id = registration.get("teamId")

    if not uid or not team_id:
        raise HTTPException(
            status_code=500,
            detail="Registration is missing its user or team ID",
        )

    team_ref = db.collection("teams").document(team_id)
    user_ref = db.collection("users").document(uid)
    manager_ref = db.collection("team_manager_profiles").document(uid)

    team_snapshot = team_ref.get()
    user_snapshot = user_ref.get()

    if not team_snapshot.exists or not user_snapshot.exists:
        raise HTTPException(
            status_code=409,
            detail="The team or user profile no longer exists",
        )

    user_data = user_snapshot.to_dict()
    global_role = str(
        user_data.get("role") or user_data.get("userRole") or ""
    ).strip().lower()

    if global_role != "team_manager":
        raise HTTPException(
            status_code=409,
            detail="The user does not have the team_manager role",
        )

    # Prevent a duplicate active membership.
    existing = (
        db.collection("team_memberships")
        .where("userId", "==", uid)
        .where("teamId", "==", team_id)
        .where("status", "==", "active")
        .limit(1)
        .stream()
    )

    if next(iter(existing), None):
        raise HTTPException(
            status_code=409,
            detail="An active membership already exists for this team",
        )

    now = datetime.now(timezone.utc)
    membership_ref = db.collection("team_memberships").document()

    batch = db.batch()

    batch.update(team_ref, {
        "status": "active",
        "approved": True,
        "approvedBy": executive_uid,
        "approvedAt": now,
        "updatedAt": now,
    })

    batch.set(membership_ref, {
        "teamId": team_id,
        "userId": uid,
        "role": "team_manager",
        "status": "active",
        "createdAt": now,
        "createdBy": executive_uid,
    })

    batch.update(registration_ref, {
        "status": "approved",
        "approvedBy": executive_uid,
        "approvedAt": now,
        "updatedAt": now,
    })

    batch.update(user_ref, {
        "status": "active",
        "updatedAt": now,
    })

    if manager_ref.get().exists:
        batch.update(manager_ref, {
            "status": "active",
            "approved": True,
            "approvedBy": executive_uid,
            "approvedAt": now,
            "updatedAt": now,
        })

    batch.commit()

    return {
        "success": True,
        "message": "Team registration approved",
        "registration_id": registration_id,
        "team_id": team_id,
        "membership_id": membership_ref.id,
        "status": "active",
    }