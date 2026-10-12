"""
Firebase initialization and authentication services.
"""

import os

import firebase_admin
from firebase_admin import auth, credentials, storage
from dotenv import load_dotenv


# Load environment variables from the project's .env file.
load_dotenv()


def initialize_firebase():
    """
    Initialize Firebase only once.

    The service-account path and Storage bucket are read
    from the project's .env file.
    """

    if firebase_admin._apps:
        return firebase_admin.get_app()

    service_account_path = os.getenv(
        "FIREBASE_SERVICE_ACCOUNT"
    )

    if not service_account_path:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT is not configured"
        )

    if not os.path.exists(service_account_path):
        raise RuntimeError(
            f"Firebase service account file not found: "
            f"{service_account_path}"
        )

    credentials_object = credentials.Certificate(
        service_account_path
    )

    storage_bucket = os.getenv(
        "FIREBASE_STORAGE_BUCKET"
    )

    if not storage_bucket:
        raise RuntimeError(
            "FIREBASE_STORAGE_BUCKET is not configured"
        )

    return firebase_admin.initialize_app(
        credentials_object,
        {
            "storageBucket": storage_bucket,
        },
    )


def verify_firebase_token(id_token: str) -> dict:
    """
    Verify a Firebase ID token and return the decoded user data.
    """
    initialize_firebase()

    return auth.verify_id_token(
        id_token,
        check_revoked=True,
    )
