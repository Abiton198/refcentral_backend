"""
Storage Service

Handles files uploaded to Firebase Cloud Storage.

Player files are kept separate from the Firestore player
record.

Storage structure:

players/
    {player_id}/
        profile/
            photo.jpg

player-documents/
    {player_id}/
        {document_id}/
            identity.pdf
"""


from firebase_admin import storage

from app.services.firebase_service import initialize_firebase


def get_bucket():
    """
    Return the Firebase Storage bucket.
    """

    initialize_firebase()

    return storage.bucket()


def upload_file(
    file_object,
    destination_path: str,
    content_type: str | None = None,
) -> str:
    """
    Upload a file to Firebase Storage.

    Returns the Storage path.

    We deliberately return the Storage path rather than
    creating a permanently public URL.

    Access to sensitive documents should be controlled
    by the backend.
    """

    bucket = get_bucket()

    blob = bucket.blob(destination_path)

    blob.upload_from_file(
        file_object,
        content_type=content_type,
    )

    return destination_path


def delete_file(
    storage_path: str,
):
    """
    Delete a file from Firebase Storage.
    """

    bucket = get_bucket()

    blob = bucket.blob(storage_path)

    if blob.exists():
        blob.delete()
