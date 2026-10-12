"""
Appointment Access Service

Controls who may access fixture information.

Access rules:

Executive
    Can view all appointments.

Referee
    Can view an appointment when appointed to it.

Team Manager
    Can view appointments involving their team.

Coach
    Can view appointments involving their team.
"""

from typing import Optional

from fastapi import HTTPException

from app.services.firestore_service import (
    get_firestore_client,
)

from app.services.team_access_service import (
    is_team_staff,
)


EXECUTIVE_ROLES = {
    "executive",
}

REFEREE_ROLES = {
    "referee",
}


# ---------------------------------------------------------
# USER
# ---------------------------------------------------------

def get_user_document(uid: str) -> Optional[dict]:
    """Retrieve a user document."""

    db = get_firestore_client()

    snapshot = (
        db.collection("users")
        .document(uid)
        .get()
    )

    if not snapshot.exists:
        return None

    data = snapshot.to_dict()

    data["uid"] = snapshot.id

    return data


def get_user_role(uid: str) -> Optional[str]:
    """Return the user's global application role."""

    user = get_user_document(uid)

    if not user:
        return None

    role = (
        user.get("role")
        or user.get("userRole")
    )

    if not role:
        return None

    return str(role).strip().lower()


# ---------------------------------------------------------
# EXECUTIVE
# ---------------------------------------------------------

def is_executive(uid: str) -> bool:
    """Check whether a user is an Executive."""

    return get_user_role(uid) in EXECUTIVE_ROLES


def require_executive(uid: str):
    """Require Executive access."""

    if not is_executive(uid):
        raise HTTPException(
            status_code=403,
            detail="Executive permission required",
        )


# ---------------------------------------------------------
# REFEREE
# ---------------------------------------------------------

def is_referee(uid: str) -> bool:
    """
    Check whether a user is a referee.

    The users collection is preferred.

    The old referees collection remains as a fallback
    for existing RefCentral data.
    """

    role = get_user_role(uid)

    if role in REFEREE_ROLES:
        return True

    db = get_firestore_client()

    referee_snapshot = (
        db.collection("referees")
        .document(uid)
        .get()
    )

    return referee_snapshot.exists


def require_referee(uid: str):
    """Require referee access."""

    if not is_referee(uid):
        raise HTTPException(
            status_code=403,
            detail="Referee permission required",
        )


# ---------------------------------------------------------
# APPOINTMENT
# ---------------------------------------------------------

def get_appointment_document(
    appointment_id: str,
) -> Optional[dict]:
    """Retrieve an appointment."""

    db = get_firestore_client()

    snapshot = (
        db.collection("appointments")
        .document(appointment_id)
        .get()
    )

    if not snapshot.exists:
        return None

    data = snapshot.to_dict()

    data["appointmentId"] = snapshot.id

    return data


def appointment_involves_team(
    appointment: dict,
    team_id: str,
) -> bool:
    """Check whether a fixture involves a particular team."""

    return (
        appointment.get("homeTeamId") == team_id
        or appointment.get("awayTeamId") == team_id
    )


# ---------------------------------------------------------
# APPOINTMENT VIEW ACCESS
# ---------------------------------------------------------

def can_view_appointment(
    uid: str,
    appointment: dict,
) -> bool:
    """
    Determine whether a user may view an appointment.

    Access is granted to:

        1. Executive
        2. Assigned referee
        3. Team Manager of home team
        4. Coach of home team
        5. Team Manager of away team
        6. Coach of away team
    """

    # -----------------------------------------------------
    # EXECUTIVE
    # -----------------------------------------------------

    if is_executive(uid):
        return True

    # -----------------------------------------------------
    # ASSIGNED REFEREE
    # -----------------------------------------------------

    if appointment.get("refereeId") == uid:
        return True

    # -----------------------------------------------------
    # HOME TEAM
    # -----------------------------------------------------

    home_team_id = appointment.get(
        "homeTeamId"
    )

    if home_team_id:
        if is_team_staff(
            uid,
            home_team_id,
        ):
            return True

    # -----------------------------------------------------
    # AWAY TEAM
    # -----------------------------------------------------

    away_team_id = appointment.get(
        "awayTeamId"
    )

    if away_team_id:
        if is_team_staff(
            uid,
            away_team_id,
        ):
            return True

    return False


def require_appointment_view_access(
    uid: str,
    appointment_id: str,
):
    """
    Require permission to view a particular appointment.

    Returns the appointment if access is granted.
    """

    appointment = get_appointment_document(
        appointment_id
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found",
        )

    if not can_view_appointment(
        uid,
        appointment,
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "You do not have permission to view "
                "this appointment"
            ),
        )

    return appointment