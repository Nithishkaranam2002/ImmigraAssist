from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.db.postgres import get_db
from app.db.models.user import User, UserRole
from app.db.models.feedback import Feedback
from app.db.models.audit_log import AuditLog
from app.api.v1.dependencies import get_current_user, require_role
from app.utils.logger import logger

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    audit_log_id: str
    is_positive: bool
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: str
    audit_log_id: str
    is_positive: bool
    comment: Optional[str]
    created_at: str


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit thumbs up or down on an answer.
    Linked to the audit log entry for that query.
    """
    # verify this user owns the answer they are rating
    result = await db.execute(
        select(AuditLog).where(
            AuditLog.id == body.audit_log_id,
            AuditLog.user_id == current_user.id,
        )
    )
    audit_log = result.scalars().first()
    if not audit_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log entry not found",
        )

    # check if already submitted feedback for this query
    existing = await db.execute(
        select(Feedback)
        .where(Feedback.audit_log_id == body.audit_log_id)
        .where(Feedback.user_id == current_user.id)
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already submitted feedback for this answer",
        )

    feedback = Feedback(
        user_id=current_user.id,
        audit_log_id=body.audit_log_id,
        is_positive=body.is_positive,
        comment=body.comment,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    logger.info(
        f"Feedback submitted by {current_user.email}: "
        f"{'👍' if body.is_positive else '👎'}"
    )

    return FeedbackResponse(
        id=str(feedback.id),
        audit_log_id=str(feedback.audit_log_id),
        is_positive=feedback.is_positive,
        comment=feedback.comment,
        created_at=str(feedback.created_at),
    )


@router.get("/", response_model=list[FeedbackResponse])
async def list_feedback(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """List all feedback. Admin only."""
    result = await db.execute(
        select(Feedback).order_by(Feedback.created_at.desc())
    )
    feedbacks = result.scalars().all()
    return [
        FeedbackResponse(
            id=str(f.id),
            audit_log_id=str(f.audit_log_id),
            is_positive=f.is_positive,
            comment=f.comment,
            created_at=str(f.created_at),
        )
        for f in feedbacks
    ]