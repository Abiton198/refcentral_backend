"""
Player Identity Document Routes

Handles National ID and passport documents.

Security:

Team Admin
    ↓
Own team
    ↓
Own player
    ↓
Upload identity document

The full identity number is never returned by the API.

The actual document file is stored in Firebase Storage.
"""


from datetime import datetime, timezone
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from app.schemas.player_document_schema import (
    PlayerDocumentResponse,
)

from app.services.firestore_service import get_firestore_client
from app.services.storage_service import upload_file
from app.services.team_access_service import (
    require_team_manager,
)

from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/api/teams",
    tags=["Player Documents"],
)


def get_db():
    """
    Return Firestore client.
    """
    return get_firestore_client()


@router.post(
    "/{team_id}/players/{player_id}/documents",
    response_model=PlayerDocumentResponse,
)
async def upload_player_document(
    team_id: str,
    player_id: str,
    document_type: str = Form(...),
    document_number: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a National ID or passport for a player.

    Only a team administrator belonging to the player's
    team can perform this operation.
    """

    uid = current_user.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    # Verify that the user administers this team.
    require_team_manager(
        uid,
        team_id,
    )

    document_type = (
        document_type
        .strip()
        .lower()
    )

    allowed_types = {
        "national_id",
        "passport",
    }

    if document_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "document_type must be "
                "'national_id' or 'passport'"
            ),
        )

    if not document_number.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document number is required",
        )

    db = get_db()

    # -----------------------------------------------------
    # Verify player exists
    # -----------------------------------------------------

    player_ref = (
        db.collection("players")
        .document(player_id)
    )

    player_snapshot = player_ref.get()

    if not player_snapshot.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found",
        )

    player = player_snapshot.to_dict()

    # -----------------------------------------------------
    # Make sure the player belongs to this team
    # -----------------------------------------------------

    if player.get("teamId") != team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This player does not belong to your team",
        )

    # -----------------------------------------------------
    # Basic file validation
    # -----------------------------------------------------

    allowed_content_types = {
        "image/jpeg",
        "image/png",
        "application/pdf",
    }

    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only PDF, JPEG and PNG files "
                "are currently supported"
            ),
        )

    # Limit upload size to 2 MB.
    maximum_size = 2 * 1024 * 1024

    file_contents = await file.read()

    if len(file_contents) > maximum_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Document must not exceed 10 MB",
        )

    # -----------------------------------------------------
    # Generate document ID
    # -----------------------------------------------------

    document_id = uuid4().hex

    now = datetime.now(timezone.utc)

    # Only keep the final four characters in normal
    # Firestore metadata.
    document_last4 = (
        document_number.strip()[-4:]
    )

    # -----------------------------------------------------
    # Storage path
    # -----------------------------------------------------

    storage_path = (
        f"player-documents/"
        f"{player_id}/"
        f"{document_id}/"
        f"{file.filename or 'identity-document'}"
    )

    # -----------------------------------------------------
    # Upload file
    # -----------------------------------------------------

    import io

    upload_file(
        io.BytesIO(file_contents),
        storage_path,
        file.content_type,
    )

    # -----------------------------------------------------
    # Firestore metadata
    # -----------------------------------------------------

    document_data = {
        "playerId": player_id,
        "documentType": document_type,
        "documentLast4": document_last4,
        "storagePath": storage_path,
        "status": "active",
        "verified": False,
        "createdAt": now,
        "updatedAt": now,
        "createdBy": uid,
    }

    (
        db.collection("player_documents")
        .document(document_id)
        .set(document_data)
    )

    return PlayerDocumentResponse(
        document_id=document_id,
        player_id=player_id,
        document_type=document_type,
        document_last4=document_last4,
        document_url=None,
        status="active",
        verified=False,
        created_at=now,
        updated_at=now,
    )
