from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from app.api.authz import ensure_admin
from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
from app.schemas.auth import TokenRead
from app.schemas.auth import UserLogin
from app.schemas.auth import UserRead
from app.schemas.auth import UserRegister
from app.schemas.auth import UserRoleUpdate
from app.services.auth_service import AuthenticationError
from app.services.auth_service import authenticate_user
from app.services.auth_service import create_access_token
from app.services.auth_service import register_user
from app.services.auth_service import set_user_role

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user_endpoint(
    payload: UserRegister,
    session: DatabaseSession,
) -> UserRead:
    try:
        user = register_user(session, payload)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenRead)
async def login_user_endpoint(
    payload: UserLogin,
    session: DatabaseSession,
) -> TokenRead:
    try:
        user = authenticate_user(session, payload.username, payload.password)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    return TokenRead(access_token=create_access_token(user))


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/users/{user_id}/role", response_model=UserRead)
async def update_user_role_endpoint(
    user_id: UUID,
    payload: UserRoleUpdate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> UserRead:
    # Only administrators may grant or change roles.
    ensure_admin(current_user)
    try:
        user = set_user_role(session, str(user_id), payload.role)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return UserRead.model_validate(user)
