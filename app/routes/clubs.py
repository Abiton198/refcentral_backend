from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.club_schema import (
    ClubCreate,
    ClubDetailsResponse,
    ClubMemberResponse,
    ClubResponse,
)

from app.services.firestore_service import get_firestore_client
from app.utils.auth import get_current_user


# Router containing all club-related API endpoints
router = APIRouter(
    prefix="/api/clubs",
    tags=["Clubs"],
)


def get_authenticated_uid(current_user: dict) -> str:
    """
    Extract the UID from the verified Firebase authentication token.

    We always use the UID provided by Firebase rather than accepting
    a user ID supplied in the request body.
    """

    user_uid = current_user.get("uid")

    if not user_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user UID was not found",
        )

    return user_uid


def get_club_membership(db, club_id: str, user_uid: str):
    """
    Check whether a user belongs to a particular club.

    Firestore path:
        clubs/{club_id}/members/{user_uid}

    Returns:
        Membership document data if the user belongs to the club.
        None if the membership does not exist.
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


def build_club_response(
    club_id: str,
    club_data: dict,
) -> ClubResponse:
    """
    Convert Firestore data into the API response format.

    Keeping this conversion in one place helps maintain consistency
    across different club endpoints.
    """

    return ClubResponse(
        club_id=club_id,
        name=club_data.get("name", ""),
        registration_number=club_data.get("registration_number"),
        email=club_data.get("email", ""),
        phone=club_data.get("phone"),
        address=club_data.get("address"),
        created_by_uid=club_data.get("created_by_uid", ""),
        status=club_data.get("status", "active"),
    )


@router.post(
    "",
    response_model=ClubResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_club(
    club_data: ClubCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Register a new rugby club.

    The authenticated user automatically becomes the club owner.
    """

    user_uid = get_authenticated_uid(current_user)

    try:
        # Connect to Firestore
        db = get_firestore_client()

        # Create a new Firestore document with an automatic ID
        club_document = db.collection("clubs").document()

        club_id = club_document.id
        current_time = datetime.now(timezone.utc)

        # Prepare the club record
        club_record = {
            "club_id": club_id,
            "name": club_data.name.strip(),
            "registration_number": club_data.registration_number,
            "email": str(club_data.email),
            "phone": club_data.phone,
            "address": club_data.address,
            "created_by_uid": user_uid,
            "status": "active",
            "created_at": current_time,
            "updated_at": current_time,
        }

        # Save the club to Firestore
        club_document.set(club_record)

        # Create the owner's membership record
        owner_reference = (
            club_document
            .collection("members")
            .document(user_uid)
        )

        owner_reference.set(
            {
                "uid": user_uid,
                "role": "owner",
                "status": "active",
                "created_at": current_time,
            }
        )

        return build_club_response(
            club_id=club_id,
            club_data=club_record,
        )

    except Exception as error:
        # Print the technical error during development
        print(f"Error creating club: {error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to register club",
        )


@router.get(
    "/my",
    response_model=list[ClubDetailsResponse],
)
def get_my_clubs(
    current_user: dict = Depends(get_current_user),
):
    """
    Return every club where the authenticated user has membership.

    A collection-group query searches all members subcollections:
        clubs/{club_id}/members/{user_uid}
    """

    user_uid = get_authenticated_uid(current_user)

    try:
        db = get_firestore_client()

        # Search every "members" subcollection for this user's UID
        membership_query = (
            db.collection_group("members")
            .where("uid", "==", user_uid)
            .stream()
        )

        clubs = []

        for membership_snapshot in membership_query:
            # Read the membership information
            membership_data = membership_snapshot.to_dict()

            # The membership document's parent is the members collection.
            # Its parent is the actual club document.
            club_reference = membership_snapshot.reference.parent.parent

            if club_reference is None:
                continue

            club_snapshot = club_reference.get()

            # Ignore memberships whose club document no longer exists
            if not club_snapshot.exists:
                continue

            club_data = club_snapshot.to_dict()

            # Build the response including the user's club role
            club_response = ClubDetailsResponse(
                club_id=club_snapshot.id,
                name=club_data.get("name", ""),
                registration_number=club_data.get(
                    "registration_number"
                ),
                email=club_data.get("email", ""),
                phone=club_data.get("phone"),
                address=club_data.get("address"),
                created_by_uid=club_data.get(
                    "created_by_uid",
                    "",
                ),
                status=club_data.get("status", "active"),
                membership=ClubMemberResponse(
                    uid=membership_data.get("uid", user_uid),
                    role=membership_data.get("role", "member"),
                    status=membership_data.get("status", "active"),
                ),
            )

            clubs.append(club_response)

        return clubs

    except Exception as error:
        print(f"Error retrieving user's clubs: {error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve clubs",
        )


@router.get(
    "/{club_id}",
    response_model=ClubDetailsResponse,
)
def get_club(
    club_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve one club.

    Security:
    - The user must have an active membership in this club.
    - A valid Firebase token alone is not enough to access every club.
    """

    user_uid = get_authenticated_uid(current_user)

    try:
        db = get_firestore_client()

        # Check whether the user belongs to this club
        membership_data = get_club_membership(
            db=db,
            club_id=club_id,
            user_uid=user_uid,
        )

        if not membership_data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this club",
            )

        # Retrieve the club document
        club_reference = db.collection("clubs").document(club_id)
        club_snapshot = club_reference.get()

        if not club_snapshot.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club not found",
            )

        club_data = club_snapshot.to_dict()

        return ClubDetailsResponse(
            club_id=club_snapshot.id,
            name=club_data.get("name", ""),
            registration_number=club_data.get(
                "registration_number"
            ),
            email=club_data.get("email", ""),
            phone=club_data.get("phone"),
            address=club_data.get("address"),
            created_by_uid=club_data.get(
                "created_by_uid",
                "",
            ),
            status=club_data.get("status", "active"),
            membership=ClubMemberResponse(
                uid=membership_data.get("uid", user_uid),
                role=membership_data.get("role", "member"),
                status=membership_data.get("status", "active"),
            ),
        )

    except HTTPException:
        # Preserve intentional HTTP errors
        raise

    except Exception as error:
        print(f"Error retrieving club: {error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve club",
        )