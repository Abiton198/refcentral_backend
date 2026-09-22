from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.club_schema import ClubCreate, ClubResponse
from app.services.firestore_service import get_firestore_client
from app.utils.auth import get_current_user


# Create a router specifically for club-related endpoints
router = APIRouter(
    prefix="/api/clubs",
    tags=["Clubs"],
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

    Authentication:
    - The user must provide a valid Firebase ID token.

    Security:
    - The creator's UID comes from Firebase authentication.
    - The frontend cannot choose or impersonate another creator.
    """

    try:
        # Get the authenticated Firebase user's UID
        user_uid = current_user.get("uid")

        # This should normally be available after Firebase verification
        if not user_uid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authenticated user UID was not found",
            )

        # Connect to Firestore
        db = get_firestore_client()

        # Reference the top-level "clubs" collection
        clubs_collection = db.collection("clubs")

        # Create a new document with an automatically generated ID
        club_document = clubs_collection.document()

        # Get the generated Firestore document ID
        club_id = club_document.id

        # Create a UTC timestamp for the new club
        current_time = datetime.now(timezone.utc)

        # Prepare the data that will be stored in Firestore
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

        # Save the club information in Firestore
        club_document.set(club_record)

        # Store the creator as the club owner
        #
        # Example Firestore path:
        # clubs/{club_id}/members/{user_uid}
        #
        # This will help us manage club administrators and members later.
        member_document = (
            club_document
            .collection("members")
            .document(user_uid)
        )

        member_document.set(
            {
                "uid": user_uid,
                "role": "owner",
                "status": "active",
                "created_at": current_time,
            }
        )

        # Return a clean response to the frontend
        return ClubResponse(
            club_id=club_id,
            name=club_record["name"],
            registration_number=club_record["registration_number"],
            email=club_record["email"],
            phone=club_record["phone"],
            address=club_record["address"],
            created_by_uid=user_uid,
            status=club_record["status"],
        )

    except HTTPException:
        # Re-raise expected HTTP errors without changing them
        raise

    except Exception as error:
        # Log the error in the terminal during development
        print(f"Error creating club: {error}")

        # Return a safe error message to the client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to register club",
        )