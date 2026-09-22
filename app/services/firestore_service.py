from firebase_admin import firestore

from app.services.firebase_service import initialize_firebase


def get_firestore_client():
    """
    Returns a Firestore client connected to our Firebase project.

    The Firebase Admin SDK is initialized before the client is created.
    """

    # Make sure Firebase has been initialized
    firebase_app = initialize_firebase()

    # Return a Firestore client using the initialized Firebase app
    return firestore.client(app=firebase_app)