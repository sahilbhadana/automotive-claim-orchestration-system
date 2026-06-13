"""Claim-level authorization policy.

Roles answer "what can this kind of user do"; ownership answers "on
which claims". Both are enforced here, server-side, so every route
shares one definition of access.
"""

from fastapi import HTTPException
from fastapi import status

from app.models.claim import Claim
from app.models.user import User
from app.models.user import UserRole

STAFF_ROLES = (UserRole.ADJUSTER, UserRole.SUPERVISOR, UserRole.ADMIN)


def is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


def can_view_claim(user: User, claim: Claim) -> bool:
    if is_staff(user):
        return True
    return claim.claimant_id is not None and claim.claimant_id == user.id


def ensure_claim_view_access(user: User, claim: Claim | None) -> Claim:
    """Return the claim, or 404 if it doesn't exist *or* the user may
    not see it. Customers get 404 rather than 403 so they cannot probe
    which claim IDs exist."""
    if claim is None or not can_view_claim(user, claim):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )
    return claim


def ensure_staff(user: User) -> None:
    if not is_staff(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action is restricted to claims staff",
        )


def ensure_admin(user: User) -> None:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action is restricted to administrators",
        )


def ensure_claimant_upload_access(user: User, claim: Claim) -> None:
    """Documents are supplied by the claim's owner, nobody else."""
    if user.role != UserRole.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can upload claim documents",
        )
    if claim.claimant_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )
