from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.member_schema import (
    MemberAdd,
    MemberResponse,
    MemberRoleUpdate,
)

from app.services.firestore_service import get_firestore_client
from app.utils.auth import get_current_user


# All member endpoints belong to a specific club.
#
# Example:
#
# /api/clubs/ABC123/members
#
router = APIRouter(
    prefix="/api/clubs/{club_id}/members",
    tags=["Members"],
)


# These are the roles that RefCentral currently supports.
ALLOWED_ROLES = {
    "owner",
    "admin",
    "coach",
    "referee",
    "player",
}


# Only these roles can manage club membership.
MEMBER_MANAGEMENT_ROLES = {
    "owner",
    "admin",
}


def get_authenticated_uid(current_user: dict) -> str:
    """
    Extract the Firebase UID from the verified authentication token.

    The UID is supplied by Firebase Admin SDK after the token
    has been successfully verified.
    """

    user_uid = current_user.get("uid")

    if not user_uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user UID was not found",
        )

    return user_uid


def get_member(
    db,
    club_id: str,
    user_uid: str,
):
    """
    Retrieve a club membership document.

    Firestore path:

        clubs/{club_id}/members/{user_uid}
    """

    member_reference = (
        db.collection("clubs")
        .document(club_id)
        .collection("members")
        .document(user_uid)
    )

    member_snapshot = member_reference.get()

    if not member_snapshot.exists:
        return None

    return member_snapshot.to_dict()


def require_member_management_access(
    db,
    club_id: str,
    user_uid: str,
):
    """
    Confirm that the authenticated user is allowed
    to manage club members.

    Only owner and admin can perform these operations.
    """

    membership = get_member(
        db=db,
        club_id=club_id,
        user_uid=user_uid,
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this club",
        )

    if membership.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your club membership is not active",
        )

    role = membership.get("role")

    if role not in MEMBER_MANAGEMENT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage members",
        )

    return membership


def build_member_response(
    club_id: str,
    member_data: dict,
) -> MemberResponse:
    """
    Convert Firestore member information into
    the standard API response.
    """

    return MemberResponse(
        uid=member_data.get("uid", ""),
        club_id=club_id,
        role=member_data.get("role", "player"),
        status=member_data.get(
            "status",
            "active",
        ),
        display_name=member_data.get(
            "display_name"
        ),
        email=member_data.get(
            "email"
        ),
    )


@router.post(
    "",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    club_id: str,
    member_data: MemberAdd,
    current_user: dict = Depends(get_current_user),
):
    """
    Add an authenticated Firebase user to a club.

    The requester must be an owner or administrator.

    The target user must already exist in Firebase Authentication.
    """

    requester_uid = get_authenticated_uid(
        current_user
    )

    try:
        db = get_firestore_client()

        # Verify that the requester has permission.
        require_member_management_access(
            db=db,
            club_id=club_id,
            user_uid=requester_uid,
        )

        # Confirm that the requested role is valid.
        role = member_data.role.strip().lower()

        if role not in ALLOWED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Invalid role. Allowed roles are: "
                    "owner, admin, coach, referee, player"
                ),
            )

        # Do not allow someone to create another owner.
        #
        # There should normally only be one owner unless
        # we later implement an explicit ownership-transfer
        # workflow.
        if role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Owner membership cannot be created "
                    "through this endpoint"
                ),
            )

        # Make sure the club exists.
        club_reference = (
            db.collection("clubs")
            .document(club_id)
        )

        club_snapshot = club_reference.get()

        if not club_snapshot.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club not found",
            )

        # The target user's UID becomes the membership
        # document ID.
        member_reference = (
            club_reference
            .collection("members")
            .document(member_data.uid)
        )

        existing_member = member_reference.get()

        # Prevent accidental duplicate memberships.
        if existing_member.exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this club",
            )

        current_time = datetime.now(timezone.utc)

        # Information stored in Firestore.
        member_record = {
            "uid": member_data.uid,
            "club_id": club_id,
            "role": role,
            "status": "active",
            "display_name": member_data.display_name,
            "email": member_data.email,
            "created_at": current_time,
            "updated_at": current_time,
        }

        # Save membership.
        member_reference.set(member_record)

        return build_member_response(
            club_id=club_id,
            member_data=member_record,
        )

    except HTTPException:
        raise

    except Exception as error:
        print(f"Error adding member: {error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to add club member",
        )


@router.get(
    "",
    response_model=list[MemberResponse],
)
def list_members(
    club_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Return all members belonging to a club.

    Any active club member can view the member list.
    """

    requester_uid = get_authenticated_uid(
        current_user
    )

    try:
        db = get_firestore_client()

        # Verify the requester belongs to the club.
        requester_membership = get_member(
            db=db,
            club_id=club_id,
            user_uid=requester_uid,
        )

        if not requester_membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this club",
            )

        if requester_membership.get("status") != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your club membership is not active",
            )

        club_reference = (
            db.collection("clubs")
            .document(club_id)
        )

        if not club_reference.get().exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club not found",
            )

        # Retrieve all club members.
        member_snapshots = (
            club_reference
            .collection("members")
            .stream()
        )

        members = []

        for member_snapshot in member_snapshots:
            member_data = member_snapshot.to_dict()

            members.append(
                build_member_response(
                    club_id=club_id,
                    member_data=member_data,
                )
            )

        return members

    except HTTPException:
        raise

    except Exception as error:
        print(f"Error listing members: {error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve club members",
        )


@router.patch(
    "/{member_uid}/role",
    response_model=MemberResponse,
)
def update_member_role(
    club_id: str,
    member_uid: str,
    role_data: MemberRoleUpdate,
    current_user: dict = Depends(get_current_user),
):
    """
    Change the role of an existing club member.

    Only owners and administrators can perform this operation.
    """

    requester_uid = get_authenticated_uid(
        current_user
    )

    try:
        db = get_firestore_client()

        requester_membership = (
            require_member_management_access(
                db=db,
                club_id=club_id,
                user_uid=requester_uid,
            )
        )

        new_role = role_data.role.strip().lower()

        if new_role not in ALLOWED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Invalid role. Allowed roles are: "
                    "owner, admin, coach, referee, player"
                ),
            )

        # Ownership must be handled through a dedicated
        # ownership-transfer process later.
        if new_role == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Owner role cannot be assigned "
                    "through this endpoint"
                ),
            )

        # Locate the member.
        member_reference = (
            db.collection("clubs")
            .document(club_id)
            .collection("members")
            .document(member_uid)
        )

        member_snapshot = member_reference.get()

        if not member_snapshot.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club member not found",
            )

        member_data = member_snapshot.to_dict()

        # Prevent an admin from changing the owner's role.
        if member_data.get("role") == "owner":
            if requester_membership.get("role") != "owner":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        "Only the club owner can manage "
                        "the owner's membership"
                    ),
                )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Owner role cannot be changed "
                    "through this endpoint"
                ),
            )

        # Update the member role.
        member_reference.update(
            {
                "role": new_role,
                "updated_at": datetime.now(timezone.utc),
            }
        )

        # Update local response data.
        member_data["role"] = new_role

        return build_member_response(
            club_id=club_id,
            member_data=member_data,
        )

    except HTTPException:
        raise

    except Exception as error:
        print(
            f"Error updating member role: {error}"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update member role",
        )


@router.patch(
    "/{member_uid}/deactivate",
    response_model=MemberResponse,
)
def deactivate_member(
    club_id: str,
    member_uid: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Deactivate a club member.

    We do not delete the membership record because historical
    records may refer to this user.
    """

    requester_uid = get_authenticated_uid(
        current_user
    )

    try:
        db = get_firestore_client()

        requester_membership = (
            require_member_management_access(
                db=db,
                club_id=club_id,
                user_uid=requester_uid,
            )
        )

        member_reference = (
            db.collection("clubs")
            .document(club_id)
            .collection("members")
            .document(member_uid)
        )

        member_snapshot = member_reference.get()

        if not member_snapshot.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club member not found",
            )

        member_data = member_snapshot.to_dict()

        # Never allow an administrator to deactivate
        # the club owner.
        if member_data.get("role") == "owner":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The club owner cannot be deactivated",
            )

        # Update status rather than deleting the document.
        member_reference.update(
            {
                "status": "inactive",
                "updated_at": datetime.now(timezone.utc),
            }
        )

        member_data["status"] = "inactive"

        return build_member_response(
            club_id=club_id,
            member_data=member_data,
        )

    except HTTPException:
        raise

    except Exception as error:
        print(
            f"Error deactivating member: {error}"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to deactivate member",
        )