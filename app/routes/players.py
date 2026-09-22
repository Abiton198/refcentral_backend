from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.player_schema import (
    PlayerCreate,
    PlayerResponse,
    PlayerUpdate,
)

from app.services.firestore_service import get_firestore_client
from app.utils.auth import get_current_user


# All player endpoints will use this router
router = APIRouter(
    prefix="/api/clubs/{club_id}/players",
    tags=["Players"],
)


# Roles permitted to register and manage players
PLAYER_MANAGEMENT_ROLES = {
    "owner",
    "admin",
}


def get_authenticated_uid(current_user: dict) -> str:
    """
    Extract the authenticated user's UID from Firebase.

    This prevents the frontend from choosing another user's UID.
    """

    user_uid = current_user.get("uid")

    if not user_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user UID was not found",
        )

    return user_uid


def get_club_member(db, club_id: str, user_uid: str):
    """
    Retrieve the user's membership record for a club.

    Firestore path:
        clubs/{club_id}/members/{user_uid}

    Returns None when the membership does not exist.
    """

    membership_reference = (
        db.collection("clubs")
        .document(club_id)
        .collection("members")
        .document(user_uid)
    )

    membership_snapshot = membership_reference.get()

    if not membership_snapshot.exists:
        return None

    return membership_snapshot.to_dict()


def require_player_management_access(
    db,
    club_id: str,
    user_uid: str,
):
    """
    Check whether the user can manage players.

    Only active owners and administrators are permitted.
    """

    # Confirm that the user belongs to the club
    membership = get_club_member(
        db=db,
        club_id=club_id,
        user_uid=user_uid,
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this club",
        )

    # Check that the membership is active
    if membership.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your club membership is not active",
        )

    # Check the user's club role
    role = membership.get("role")

    if role not in PLAYER_MANAGEMENT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage players",
        )

    return membership


def get_player_response(
    player_id: str,
    club_id: str,
    player_data: dict,
) -> PlayerResponse:
    """
    Convert Firestore player data into a validated API response.

    This keeps the response format consistent across endpoints.
    """

    return PlayerResponse(
        player_id=player_id,
        club_id=club_id,
        full_name=player_data.get("full_name", ""),
        date_of_birth=player_data.get("date_of_birth", ""),
        registration_number=player_data.get(
            "registration_number"
        ),
        playing_position=player_data.get(
            "playing_position"
        ),
        jersey_number=player_data.get("jersey_number"),
        emergency_contact_name=player_data.get(
            "emergency_contact_name"
        ),
        emergency_contact_phone=player_data.get(
            "emergency_contact_phone"
        ),
        registered_by_uid=player_data.get(
            "registered_by_uid",
            "",
        ),
        status=player_data.get("status", "active"),
    )


@router.post(
    "",
    response_model=PlayerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_player(
    club_id: str,
    player_data: PlayerCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Register a new player under a specific club.

    Process:
    1. Authenticate the user through Firebase.
    2. Verify the user's club membership and role.
    3. Create a player document.
    4. Save the player in the club's players subcollection.
    """

    user_uid = get_authenticated_uid(current_user)

    try:
        # Connect to Firestore
        db = get_firestore_client()

        # Only club owners and administrators can register players
        require_player_management_access(
            db=db,
            club_id=club_id,
            user_uid=user_uid,
        )

        # Confirm that the parent club exists
        club_reference = db.collection("clubs").document(club_id)
        club_snapshot = club_reference.get()

        if not club_snapshot.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club not found",
            )

        # Create a new player document with an automatic ID
        player_reference = club_reference.collection(
            "players"
        ).document()

        player_id = player_reference.id
        current_time = datetime.now(timezone.utc)

        # Prepare the player information
        player_record = {
            "player_id": player_id,
            "club_id": club_id,
            "full_name": player_data.full_name.strip(),
            "date_of_birth": player_data.date_of_birth,
            "registration_number": (
                player_data.registration_number
            ),
            "playing_position": (
                player_data.playing_position
            ),
            "jersey_number": player_data.jersey_number,
            "emergency_contact_name": (
                player_data.emergency_contact_name
            ),
            "emergency_contact_phone": (
                player_data.emergency_contact_phone
            ),
            "registered_by_uid": user_uid,
            "status": "active",
            "created_at": current_time,
            "updated_at": current_time,
        }

        # Save the player record to Firestore
        player_reference.set(player_record)

        # Return the newly created player
        return get_player_response(
            player_id=player_id,
            club_id=club_id,
            player_data=player_record,
        )

    except HTTPException:
        # Preserve intentional HTTP errors
        raise

    except Exception as error:
        # Print technical details during local development
        print(f"Error creating player: {error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to register player",
        )


@router.get(
    "",
    response_model=list[PlayerResponse],
)
def list_players(
    club_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    List all active players belonging to a club.

    Any active club member can view the player list.
    """

    user_uid = get_authenticated_uid(current_user)

    try:
        # Connect to Firestore
        db = get_firestore_client()

        # Verify that the user belongs to this club
        membership = get_club_member(
            db=db,
            club_id=club_id,
            user_uid=user_uid,
        )

        if not membership or membership.get("status") != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this club",
            )

        # Confirm that the club exists
        club_reference = db.collection("clubs").document(club_id)

        if not club_reference.get().exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club not found",
            )

        # Retrieve the players subcollection
        players_query = (
            club_reference
            .collection("players")
            .where("status", "==", "active")
            .stream()
        )

        players = []

        for player_snapshot in players_query:
            player_data = player_snapshot.to_dict()

            players.append(
                get_player_response(
                    player_id=player_snapshot.id,
                    club_id=club_id,
                    player_data=player_data,
                )
            )

        return players

    except HTTPException:
        raise

    except Exception as error:
        print(f"Error listing players: {error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve players",
        )


@router.get(
    "/{player_id}",
    response_model=PlayerResponse,
)
def get_player(
    club_id: str,
    player_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve one player from a club.

    The authenticated user must be an active member of the club.
    """

    user_uid = get_authenticated_uid(current_user)

    try:
        # Connect to Firestore
        db = get_firestore_client()

        # Verify club membership
        membership = get_club_member(
            db=db,
            club_id=club_id,
            user_uid=user_uid,
        )

        if not membership or membership.get("status") != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this club",
            )

        # Build the player document reference
        player_reference = (
            db.collection("clubs")
            .document(club_id)
            .collection("players")
            .document(player_id)
        )

        # Retrieve the player document
        player_snapshot = player_reference.get()

        if not player_snapshot.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Player not found",
            )

        player_data = player_snapshot.to_dict()

        # Return the player information
        return get_player_response(
            player_id=player_snapshot.id,
            club_id=club_id,
            player_data=player_data,
        )

    except HTTPException:
        raise

    except Exception as error:
        print(f"Error retrieving player: {error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve player",
        )

@router.patch(
    "/{player_id}",
    response_model=PlayerResponse,
)
def update_player(
    club_id: str,
    player_id: str,
    player_data: PlayerUpdate,
    current_user: dict = Depends(get_current_user),
):
    """
    Update an existing player's information.

    Only active club owners and administrators can perform updates.
    """

    user_uid = get_authenticated_uid(current_user)

    try:
        # Connect to Firestore
        db = get_firestore_client()

        # Confirm that the user has player-management permissions
        require_player_management_access(
            db=db,
            club_id=club_id,
            user_uid=user_uid,
        )

        # Reference the requested player document
        player_reference = (
            db.collection("clubs")
            .document(club_id)
            .collection("players")
            .document(player_id)
        )

        player_snapshot = player_reference.get()

        if not player_snapshot.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Player not found",
            )

        # Get only fields actually provided in the request
        update_data = player_data.model_dump(
            exclude_unset=True
        )

        # Remove whitespace from the player's name
        if "full_name" in update_data:
            update_data["full_name"] = (
                update_data["full_name"].strip()
            )

        # Prevent duplicate registration numbers
        if (
            "registration_number" in update_data
            and update_data["registration_number"]
        ):
            duplicate_query = (
                db.collection("clubs")
                .document(club_id)
                .collection("players")
                .where(
                    "registration_number",
                    "==",
                    update_data["registration_number"],
                )
                .stream()
            )

            for duplicate in duplicate_query:
                # Exclude the player currently being updated
                if duplicate.id != player_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "This registration number is already "
                            "used by another player"
                        ),
                    )

        # Add the time of the update
        update_data["updated_at"] = datetime.now(timezone.utc)

        # Apply the changes to Firestore
        player_reference.update(update_data)

        # Read the updated document
        updated_snapshot = player_reference.get()
        updated_data = updated_snapshot.to_dict()

        # Return the updated player
        return get_player_response(
            player_id=player_id,
            club_id=club_id,
            player_data=updated_data,
        )

    except HTTPException:
        raise

    except Exception as error:
        print(f"Error updating player: {error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update player",
        )


@router.patch(
    "/{player_id}/deactivate",
    response_model=PlayerResponse,
)
def deactivate_player(
    club_id: str,
    player_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Deactivate a player without deleting their record.

    This preserves historical registration and match-related data
    for future reporting.
    """

    user_uid = get_authenticated_uid(current_user)

    try:
        # Connect to Firestore
        db = get_firestore_client()

        # Only authorized club administrators can deactivate players
        require_player_management_access(
            db=db,
            club_id=club_id,
            user_uid=user_uid,
        )

        # Reference the player document
        player_reference = (
            db.collection("clubs")
            .document(club_id)
            .collection("players")
            .document(player_id)
        )

        player_snapshot = player_reference.get()

        if not player_snapshot.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Player not found",
            )

        # Update status instead of permanently deleting the record
        player_reference.update(
            {
                "status": "inactive",
                "updated_at": datetime.now(timezone.utc),
            }
        )

        # Read the updated player document
        updated_snapshot = player_reference.get()
        updated_data = updated_snapshot.to_dict()

        return get_player_response(
            player_id=player_id,
            club_id=club_id,
            player_data=updated_data,
        )

    except HTTPException:
        raise

    except Exception as error:
        print(f"Error deactivating player: {error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to deactivate player",
        )