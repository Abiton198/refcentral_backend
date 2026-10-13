"""
Firebase initialization and authentication services.
"""

import json
import logging
import os

import firebase_admin
from firebase_admin import auth, credentials
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def _load_credentials():
    value = os.getenv("FIREBASE_SERVICE_ACCOUNT", "").strip()

    if not value:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT is not configured")

    # Accept raw JSON pasted into the env var...
    if value.startswith("{"):
        return credentials.Certificate(json.loads(value))

    # ...or a path to the JSON file (e.g. /etc/secrets/serviceAccount.json)
    if not os.path.exists(value):
        raise RuntimeError(f"Firebase service account file not found: {value}")

    return credentials.Certificate(value)


def initialize_firebase():
    if firebase_admin._apps:
        return firebase_admin.get_app()

    storage_bucket = os.getenv("FIREBASE_STORAGE_BUCKET")
    if not storage_bucket:
        raise RuntimeError("FIREBASE_STORAGE_BUCKET is not configured")

    return firebase_admin.initialize_app(
        _load_credentials(),
        {"storageBucket": storage_bucket},
    )


def verify_firebase_token(id_token: str) -> dict:
    app = initialize_firebase()
    try:
        return auth.verify_id_token(id_token, check_revoked=True)
    except Exception as e:
        logger.error(
            "Token verification failed: %s: %s | backend project: %s",
            type(e).__name__, e, app.project_id,
        )
        raise