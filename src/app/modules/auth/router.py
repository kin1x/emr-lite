from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AlreadyExistsException, UnauthorizedException
from app.modules.auth.service import AuthService
from app.modules.auth.dependencies import get_current_user
from app.schemas.user import UserCreate, UserResponse
from app.schemas.common import MessageResponse
from app.models.user import User

router = APIRouter()
security = HTTPBearer()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    try:
        user = await service.register(data)
        return user
    except AlreadyExistsException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/login",
    summary="Login and get JWT tokens",
)
async def login(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email and password are required",
        )

    service = AuthService(db)
    try:
        tokens = await service.login(email=email, password=password)
        return tokens
    except UnauthorizedException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/refresh",
    summary="Refresh access token",
)
async def refresh_token(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="refresh_token is required",
        )

    service = AuthService(db)
    try:
        tokens = await service.refresh(refresh_token)
        return tokens
    except UnauthorizedException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout and revoke tokens",
)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    await service.logout(
        user=current_user,
        access_token=credentials.credentials,
    )
    return MessageResponse(message="Successfully logged out")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user