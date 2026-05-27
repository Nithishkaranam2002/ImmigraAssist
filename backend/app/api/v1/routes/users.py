from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.db.postgres import get_db
from app.db.models.user import User, UserRole
from app.api.v1.dependencies import get_current_user, require_role
from app.utils.logger import logger

router = APIRouter(prefix="/users", tags=["users"])


class UserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    role: str
    is_active: bool
    created_at: str


class UpdateRoleRequest(BaseModel):
    role: UserRole


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


@router.get("/", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """List all users. Admin only."""
    result = await db.execute(
        select(User).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        UserResponse(
            id=str(u.id),
            full_name=u.full_name,
            email=u.email,
            role=u.role.value,
            is_active=u.is_active,
            created_at=str(u.created_at),
        )
        for u in users
    ]


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Get currently logged-in user profile."""
    return UserResponse(
        id=str(current_user.id),
        full_name=current_user.full_name,
        email=current_user.email,
        role=current_user.role.value,
        is_active=current_user.is_active,
        created_at=str(current_user.created_at),
    )


@router.patch("/{user_id}/role")
async def update_user_role(
    user_id: str,
    body: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Update a user's role. Admin only."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    old_role = user.role
    user.role = body.role
    await db.commit()

    logger.info(
        f"User {user.email} role changed: "
        f"{old_role} → {body.role} by {current_user.email}"
    )

    return {"message": f"Role updated to {body.role.value}"}


@router.patch("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Deactivate a user account. Admin only."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = False
    await db.commit()

    logger.info(
        f"User {user.email} deactivated by {current_user.email}"
    )

    return {"message": "User deactivated successfully"}