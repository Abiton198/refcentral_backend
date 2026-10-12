"""
Team Access Service

This module controls permissions for users who belong to a rugby team.

Team-scoped roles:
    team_manager
    coach

Important:
    Executive is NOT a team membership role.

    A user becomes a Team Manager or Coach for a particular team
    through the `team_memberships` collection.

Temporary compatibility:
    `team_admin` is accepted as an alias for `team_manager`
    so existing test memberships do not immediately break.

New memberships must NEVER be created with `team_admin`.
"""

from typing import Optional, Iterable

from fastapi import HTTPException, status

from app.services.firestore_service import get_firestore_client


# ---------------------------------------------------------
# ROLE DEFINITIONS
# ---------------------------------------------------------

TEAM_MANAGER_ROLES = {
    "team_manager",

    # Temporary compatibility for existing Firestore data.
    # Remove this after old memberships are migrated.
    "team_admin",
}

TEAM_COACH_ROLES = {
    "coach",
}

TEAM_STAFF_ROLES = (
    TEAM_MANAGER_ROLES
    | TEAM_COACH_ROLES
)


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

def get_db():
    """Return the Firestore client."""
    return get_firestore_client()


# ---------------------------------------------------------
# TEAM
# ---------------------------------------------------------

def get_team(team_id: str) -> Optional[dict]:
    """
    Retrieve a team by its Firestore document ID.

    Returns:
        Team dictionary if found.
        None if the team does not exist.
    """

    db = get_db()

    snapshot = (
        db.collection("teams")
        .document(team_id)
        .get()
    )

    if not snapshot.exists:
        return None

    data = snapshot.to_dict()

    # Existing team records may not yet contain status.
    # Treat them as active for backwards compatibility.
    data["teamId"] = snapshot.id

    if not data.get("status"):
        data["status"] = "active"

    return data


# ---------------------------------------------------------
# MEMBERSHIP
# ---------------------------------------------------------

def get_user_membership(
    uid: str,
    team_id: str,
) -> Optional[dict]:
    """
    Find the active membership for a user on a team.

    A membership connects:

        userId
        +
        teamId
        +
        role

    Example:

        {
            "userId": "...",
            "teamId": "...",
            "role": "team_manager",
            "status": "active"
        }
    """

    db = get_db()

    memberships = (
        db.collection("team_memberships")
        .where("userId", "==", uid)
        .where("teamId", "==", team_id)
        .where("status", "==", "active")
        .limit(10)
        .stream()
    )

    for membership in memberships:
        data = membership.to_dict()

        data["membershipId"] = membership.id

        return data

    return None


def get_team_role(
    uid: str,
    team_id: str,
) -> Optional[str]:
    """
    Return the user's role on a particular team.

    Example:
        "team_manager"
        "coach"
        None
    """

    membership = get_user_membership(
        uid,
        team_id,
    )

    if not membership:
        return None

    role = membership.get("role")

    if not role:
        return None

    return str(role).strip().lower()


# ---------------------------------------------------------
# GENERIC ROLE CHECK
# ---------------------------------------------------------

def has_team_role(
    uid: str,
    team_id: str,
    allowed_roles: Iterable[str],
) -> bool:
    """
    Check whether a user has one of the supplied roles
    on a particular team.
    """

    role = get_team_role(
        uid,
        team_id,
    )

    if not role:
        return False

    allowed = {
        str(item).strip().lower()
        for item in allowed_roles
    }

    return role in allowed


# ---------------------------------------------------------
# TEAM MANAGER
# ---------------------------------------------------------

def is_team_manager(
    uid: str,
    team_id: str,
) -> bool:
    """
    Team Managers can administer their team's
    player registration and team administration.

    `team_admin` remains temporarily accepted as a
    legacy alias.
    """

    return has_team_role(
        uid,
        team_id,
        TEAM_MANAGER_ROLES,
    )


def require_team_manager(
    uid: str,
    team_id: str,
):
    """
    Require Team Manager permission.

    Raises:
        404 if team does not exist.
        403 if user is not a Team Manager.
    """

    team = get_team(team_id)

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    if not is_team_manager(uid, team_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You do not have Team Manager permission "
                "for this team"
            ),
        )

    return team


# ---------------------------------------------------------
# COACH
# ---------------------------------------------------------

def is_team_coach(
    uid: str,
    team_id: str,
) -> bool:
    """Check whether the user is an active Coach for the team."""

    return has_team_role(
        uid,
        team_id,
        TEAM_COACH_ROLES,
    )


def require_team_coach(
    uid: str,
    team_id: str,
):
    """Require Coach permission for a team."""

    team = get_team(team_id)

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    if not is_team_coach(uid, team_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You do not have Coach permission "
                "for this team"
            ),
        )

    return team


# ---------------------------------------------------------
# TEAM STAFF
# ---------------------------------------------------------

def is_team_staff(
    uid: str,
    team_id: str,
) -> bool:
    """
    Check whether the user is either:

        Team Manager
        OR
        Coach
    """

    return has_team_role(
        uid,
        team_id,
        TEAM_STAFF_ROLES,
    )


def require_team_staff(
    uid: str,
    team_id: str,
):
    """
    Require either Team Manager or Coach permission.

    Useful for operations where both roles can view
    team information.
    """

    team = get_team(team_id)

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    if not is_team_staff(uid, team_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You do not have permission to access "
                "this team"
            ),
        )

    return team