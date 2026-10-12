"""
Player Photo Routes

Handles player profile photographs.

Photos are stored privately in Firebase Storage.

Security model:

Team Admin
    ↓
Own team
    ↓
Own player
    ↓
Upload / replace photo

Referee access will be added later through the matchday
appointment authorization system.

The frontend does not receive a permanent public Firebase
Storage URL.
"""


from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

from app.services.firestore_service import get_firestore_client
from app.services.storage_service import (
    delete_file,
    get_bucket,
    upload_file,
)

from app.services.team_access_service import (
    require_team_manager,
)

from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/api/teams",
    tags=["Player Photos"],
)


def get_db():
    """
    Return Firestore client.
    """
    return get_firestore_client()


def get_player_for_team(
    team_id: str,
    player_id: str,
):
    """
    Retrieve a player and verify that the player belongs
    to the requested team.
    """

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

    if player.get("teamId") != team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This player does not belong to this team",
        )

    return player_ref, player


# ---------------------------------------------------------
# Upload / replace player photo
# ---------------------------------------------------------

@router.post(
    "/{team_id}/players/{player_id}/photo",
)
async def upload_player_photo(
    team_id: str,
    player_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload or replace a player's profile photograph.

    Only an administrator of the player's team can perform
    this operation.
    """

    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    # Verify team administrator permission.
    require_team_manager(
        uid,
        team_id,
    )

    player_ref, player = get_player_for_team(
        team_id,
        player_id,
    )

    # -----------------------------------------------------
    # Validate file type
    # -----------------------------------------------------

    allowed_content_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only JPEG, PNG and WebP images "
                "are currently supported"
            ),
        )

    # -----------------------------------------------------
    # Read file
    # -----------------------------------------------------

    file_contents = await file.read()

    # Maximum photo size: 5 MB.
    maximum_size = 5 * 1024 * 1024

    if len(file_contents) > maximum_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Player photo must not exceed 5 MB",
        )

    if not file_contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded photo is empty",
        )

    # -----------------------------------------------------
    # Fixed storage location
    # -----------------------------------------------------

    storage_path = (
        f"players/"
        f"{player_id}/"
        f"profile/"
        f"photo"
    )

    # -----------------------------------------------------
    # Upload photo
    # -----------------------------------------------------

    import io

    upload_file(
        io.BytesIO(file_contents),
        storage_path,
        file.content_type,
    )

    # -----------------------------------------------------
    # Store only the protected storage path in Firestore.
    # -----------------------------------------------------

    photo_api_url = (
        f"/api/teams/"
        f"{team_id}/"
        f"players/"
        f"{player_id}/"
        f"photo"
    )

    player_ref.update(
        {
            "photoStoragePath": storage_path,
            "photoUrl": photo_api_url,
            "updatedBy": uid,
        }
    )

    return {
        "success": True,
        "message": "Player photo uploaded successfully",
        "player_id": player_id,
        "photo_url": photo_api_url,
    }


# ---------------------------------------------------------
# View player photo
# ---------------------------------------------------------

@router.get(
    "/{team_id}/players/{player_id}/photo",
)
def get_player_photo(
    team_id: str,
    player_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Return a player's private photo.

    At this stage only team administrators of the player's
    team can view it.

    Later we will extend this permission to referees when
    they are inspecting players for an assigned match.
    """

    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    # Current access rule:
    # team administrator of this team.
    require_team_manager(
        uid,
        team_id,
    )

    _, player = get_player_for_team(
        team_id,
        player_id,
    )

    storage_path = player.get(
        "photoStoragePath"
    )

    if not storage_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player does not have a photo",
        )

    bucket = get_bucket()

    blob = bucket.blob(storage_path)

    if not blob.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player photo file not found",
        )

    # Download the private file from Firebase Storage.
    photo_bytes = blob.download_as_bytes()

    content_type = (
        blob.content_type
        or "image/jpeg"
    )

    return StreamingResponse(
        iter([photo_bytes]),
        media_type=content_type,
        headers={
            "Cache-Control": "private, max-age=300",
        },
    )


# ---------------------------------------------------------
# Delete player photo
# ---------------------------------------------------------

@router.delete(
    "/{team_id}/players/{player_id}/photo",
)
def delete_player_photo(
    team_id: str,
    player_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Remove a player's profile photograph.
    """

    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    require_team_manager(
        uid,
        team_id,
    )

    player_ref, player = get_player_for_team(
        team_id,
        player_id,
    )

    storage_path = player.get(
        "photoStoragePath"
    )

    if storage_path:
        delete_file(storage_path)

    player_ref.update(
        {
            "photoStoragePath": None,
            "photoUrl": None,
            "updatedBy": uid,
        }
    )

    return {
        "success": True,
        "message": "Player photo removed",
        "player_id": player_id,
    }
