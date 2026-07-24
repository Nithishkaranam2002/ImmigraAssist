import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.db.postgres import get_db
from app.db.models.user import User, UserRole
from app.db.models.invite import Invite
from app.api.v1.dependencies import require_role
from app.core.permissions import can_assign_role
from app.utils.logger import logger

router = APIRouter(prefix="/invites", tags=["invites"])


class CreateInviteRequest(BaseModel):
    email: Optional[EmailStr] = None
    role: UserRole = UserRole.ATTORNEY
    designation: Optional[str] = None


class InviteResponse(BaseModel):
    id: str
    token: str
    email: Optional[str]
    role: str
    designation: Optional[str]
    invite_link: str
    expires_at: str
    is_used: bool


@router.post("/", response_model=InviteResponse)
async def create_invite(
    body: CreateInviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Create an invite link for a new attorney or admin.
    Admin only.
    """
    if not can_assign_role(current_user.role, body.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot invite a role above your own level",
        )

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    invite = Invite(
        token=token,
        email=body.email,
        role=body.role,
        designation=body.designation,
        created_by=current_user.id,
        expires_at=expires_at,
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    invite_link = f"http://localhost:5173/signup?token={token}"

    logger.info(
        f"Invite created by {current_user.email} "
        f"for role={body.role} email={body.email}"
    )

    return InviteResponse(
        id=str(invite.id),
        token=token,
        email=invite.email,
        role=invite.role.value,
        designation=invite.designation,
        invite_link=invite_link,
        expires_at=str(invite.expires_at),
        is_used=invite.is_used,
    )


@router.get("/validate/{token}")
async def validate_invite(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Validate an invite token before signup.
    Returns role and designation pre-set for this invite.
    """
    result = await db.execute(
        select(Invite).where(Invite.token == token)
    )
    invite = result.scalars().first()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite link",
        )

    if invite.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite link has already been used",
        )

    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite link has expired",
        )

    return {
        "valid": True,
        "role": invite.role.value,
        "designation": invite.designation,
        "email": invite.email,
    }


@router.get("/", response_model=list[InviteResponse])
async def list_invites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """List all invites. Admin only."""
    result = await db.execute(
        select(Invite).order_by(Invite.created_at.desc())
    )
    invites = result.scalars().all()
    return [
        InviteResponse(
            id=str(i.id),
            token=i.token,
            email=i.email,
            role=i.role.value,
            designation=i.designation,
            invite_link=f"http://localhost:5173/signup?token={i.token}",
            expires_at=str(i.expires_at),
            is_used=i.is_used,
        )
        for i in invites
    ]