import os

import firebase_admin
from firebase_admin import auth, credentials


def initialize_firebase():
    if firebase_admin._apps:
        return firebase_admin.get_app()

    service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT")

    if not service_account_path:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT is not configured"
        )

    if not os.path.exists(service_account_path):
        raise RuntimeError(
            "Firebase service account file not found"
        )

    cred = credentials.Certificate(service_account_path)

    return firebase_admin.initialize_app(cred)


def verify_firebase_token(id_token: str) -> dict:
    initialize_firebase()

    decoded_token = auth.verify_id_token(
        id_token,
        check_revoked=True,
    )

    return decoded_token
