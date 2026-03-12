from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.redis import redis_client
from app.core.config import settings
from sqlalchemy.exc import IntegrityError
from app.core.exceptions import (
    AlreadyExistsException,
    UnauthorizedException,
    NotFoundException,
)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: UserCreate) -> User:
        result = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise AlreadyExistsException(f"User with email '{data.email}'")

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            role=data.role,
        )
        self.db.add(user)
        try:
            await self.db.flush()
            await self.db.refresh(user)
        except IntegrityError:
            await self.db.rollback()
            raise AlreadyExistsException(f"User with email '{data.email}'")
        return user

    async def login(self, email: str, password: str) -> dict:
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedException("Invalid email or password")

        if not user.is_active:
            raise UnauthorizedException("Account is disabled")

        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))

        await redis_client.set(
            key=f"refresh:{user.id}",
            value=refresh_token,
            expire=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user_id": str(user.id),
            "role": user.role.value,
        }

    async def refresh(self, refresh_token: str) -> dict:
        try:
            payload = decode_token(refresh_token)
        except ValueError:
            raise UnauthorizedException("Invalid or expired refresh token")

        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type")

        user_id = payload.get("sub")

        stored_token = await redis_client.get(f"refresh:{user_id}")
        if not stored_token or stored_token != refresh_token:
            raise UnauthorizedException("Refresh token is invalid or revoked")

        result = await self.db.execute(
            select(User).where(User.id == str(user_id))
        )
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise UnauthorizedException("User not found or disabled")

        new_access_token = create_access_token(subject=str(user.id))
        new_refresh_token = create_refresh_token(subject=str(user.id))

        await redis_client.set(
            key=f"refresh:{user.id}",
            value=new_refresh_token,
            expire=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        )

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    async def logout(self, user: User, access_token: str) -> None:
        await redis_client.set(
            key=f"blacklist:{access_token}",
            value="1",
            expire=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        await redis_client.delete(f"refresh:{user.id}")

    async def get_user_by_id(self, user_id: str) -> User:
        result = await self.db.execute(
            select(User).where(User.id == str(user_id))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundException("User", user_id)
        return user