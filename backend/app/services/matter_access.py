from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat_query_meta import ChatQueryMeta
from app.db.models.matter import Matter


async def require_owned_matter(
    db: AsyncSession,
    matter_id: UUID,
    user_id: UUID,
) -> Matter:
    """Return a matter only when it belongs to the requesting user."""
    result = await db.execute(
        select(Matter).where(Matter.id == matter_id, Matter.user_id == user_id)
    )
    matter = result.scalars().first()
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")
    return matter


async def detach_matter_research(db: AsyncSession, matter_id: UUID) -> None:
    """Ungroup all retained research before deleting its matter."""
    await db.execute(
        update(ChatQueryMeta)
        .where(ChatQueryMeta.matter_id == matter_id)
        .values(matter_id=None)
    )
