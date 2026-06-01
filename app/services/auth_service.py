from __future__ import annotations

from uuid import UUID

from datetime import UTC
from datetime import datetime
from datetime import timedelta

import jwt
from passlib.context import CryptContext
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.models.user import UserRole
from app.schemas.auth import UserRegister

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationError(ValueError):
    pass


def register_user(session: Session, payload: UserRegister) -> User:
    existing = session.scalar(
        select(User).where(
            or_(User.username == payload.username, User.email == payload.email)
        )
    )
    if existing is not None:
        raise AuthenticationError("Username or email already exists")

    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate_user(session: Session, username: str, password: str) -> User:
    user = session.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid username or password")
    if not user.is_active:
        raise AuthenticationError("User account is inactive")
    return user


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.scalar(select(User).where(User.username == username))


def get_user_by_id(session: Session, user_id: str) -> User | None:
    return session.get(User, UUID(user_id))


def create_access_token(user: User) -> str:
    expire_at = datetime.now(UTC) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value,
        "exp": expire_at,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired access token") from exc


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)
