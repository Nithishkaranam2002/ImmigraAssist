from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timezone
from app.db.postgres import get_db
from app.db.models.user import User, UserRole
from app.db.models.invite import Invite
from app.core.security import hash_password, verify_password, create_access_token
from app.utils.logger import logger

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    designation: Optional[str] = None
    invite_token: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    full_name: str
    designation: Optional[str] = None


async def _load_invite_for_registration(
    db: AsyncSession,
    token: str,
    email: str,
) -> Invite:
    """
    Load an invite for registration under a row lock.

    SELECT ... FOR UPDATE serializes concurrent registrations that share the
    same invite token so an email-less ("general") invite cannot mint multiple
    privileged accounts before is_used is committed.
    """
    invite_result = await db.execute(
        select(Invite).where(Invite.token == token).with_for_update()
    )
    invite = invite_result.scalars().first()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invite token",
        )
    if invite.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite already used",
        )
    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite has expired",
        )
    if invite.email and invite.email != email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite was created for a different email",
        )

    return invite


@router.post("/register", response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.
    If invite_token is provided, use role and designation from invite.
    Otherwise default to junior_associate.
    """
    result = await db.execute(
        select(User).where(User.email == body.email)
    )
    existing = result.scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    role = UserRole.JUNIOR_ASSOCIATE
    designation = body.designation
    invite = None

    if body.invite_token:
        invite = await _load_invite_for_registration(
            db, body.invite_token, body.email
        )
        role = invite.role
        designation = invite.designation or body.designation

    user = User(
        full_name=body.full_name,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=role,
        designation=designation,
        is_active=True,
        is_verified=True if invite else False,
    )
    db.add(user)

    if invite:
        invite.is_used = True
        invite.used_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user)

    token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )

    logger.info(f"New user registered: {user.email} ({user.role})")

    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        role=user.role.value,
        full_name=user.full_name,
        designation=user.designation,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.email == body.email)
    )
    user = result.scalars().first()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your administrator.",
        )

    token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )

    logger.info(f"User logged in: {user.email}")

    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        role=user.role.value,
        full_name=user.full_name,
        designation=user.designation,
    )