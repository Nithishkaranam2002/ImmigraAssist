from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from app.db.models.audit_log import AuditLog
from app.db.models.chat_query_meta import ChatQueryMeta
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from app.db.postgres import get_db
from app.db.models.user import User
from app.db.models.matter import Matter
from app.api.v1.dependencies import get_current_user

router = APIRouter(prefix="/matters", tags=["matters"])


class MatterCreate(BaseModel):
    title: str
    client_name: Optional[str] = None
    visa_type: Optional[str] = None
    description: Optional[str] = None


class MatterUpdate(BaseModel):
    title: Optional[str] = None
    client_name: Optional[str] = None
    visa_type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class AttachResearchRequest(BaseModel):
    """Save chat research to a new or existing matter."""
    matter_id: Optional[UUID] = None
    title: Optional[str] = None
    client_name: Optional[str] = None
    visa_type: Optional[str] = None
    description: Optional[str] = None
    audit_log_ids: list[UUID] = []
    session_id: Optional[UUID] = None


@router.get("/")
async def list_matters(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(
            Matter,
            func.count(ChatQueryMeta.audit_log_id).label("query_count"),
        )
        .outerjoin(ChatQueryMeta, ChatQueryMeta.matter_id == Matter.id)
        .where(Matter.user_id == current_user.id)
        .group_by(Matter.id)
        .order_by(Matter.updated_at.desc().nullslast(), Matter.created_at.desc())
    )
    return [
        {
            "id": str(m.id),
            "title": m.title,
            "client_name": m.client_name,
            "visa_type": m.visa_type,
            "description": m.description,
            "status": m.status,
            "created_at": str(m.created_at),
            "query_count": int(query_count or 0),
        }
        for m, query_count in result.all()
    ]


@router.get("/{matter_id}")
async def get_matter(
    matter_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Matter).where(Matter.id == matter_id, Matter.user_id == current_user.id)
    )
    matter = result.scalars().first()
    if not matter:
        raise HTTPException(404, "Matter not found")
    return {
        "id": str(matter.id),
        "title": matter.title,
        "client_name": matter.client_name,
        "visa_type": matter.visa_type,
        "description": matter.description,
        "status": matter.status,
        "created_at": str(matter.created_at),
        "updated_at": str(matter.updated_at) if matter.updated_at else None,
    }


@router.post("/attach-research")
async def attach_research(
    body: AttachResearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or select a matter and link chat queries from this session."""
    if body.matter_id:
        result = await db.execute(
            select(Matter).where(Matter.id == body.matter_id, Matter.user_id == current_user.id)
        )
        matter = result.scalars().first()
        if not matter:
            raise HTTPException(404, "Matter not found")
    else:
        if not body.title or not body.title.strip():
            raise HTTPException(400, "Title is required when creating a new matter")
        matter = Matter(
            user_id=current_user.id,
            title=body.title.strip(),
            client_name=body.client_name,
            visa_type=body.visa_type,
            description=body.description,
        )
        db.add(matter)
        await db.flush()

    audit_ids: list[UUID] = list(body.audit_log_ids)
    if body.session_id:
        result = await db.execute(
            select(ChatQueryMeta.audit_log_id)
            .join(AuditLog, AuditLog.id == ChatQueryMeta.audit_log_id)
            .where(
                ChatQueryMeta.session_id == body.session_id,
                AuditLog.user_id == current_user.id,
            )
        )
        session_audit_ids = [row[0] for row in result.fetchall()]
        audit_ids = list(dict.fromkeys([*audit_ids, *session_audit_ids]))

    if not audit_ids:
        raise HTTPException(400, "No research queries to attach")

    attached = 0
    for audit_id in audit_ids:
        log_result = await db.execute(
            select(AuditLog).where(AuditLog.id == audit_id, AuditLog.user_id == current_user.id)
        )
        if not log_result.scalars().first():
            continue

        meta_result = await db.execute(
            select(ChatQueryMeta).where(ChatQueryMeta.audit_log_id == audit_id)
        )
        meta = meta_result.scalars().first()
        if meta:
            meta.matter_id = matter.id
            attached += 1
        else:
            db.add(
                ChatQueryMeta(
                    audit_log_id=audit_id,
                    matter_id=matter.id,
                    session_id=body.session_id,
                    query_mode="standard",
                )
            )
            attached += 1

    if attached == 0:
        raise HTTPException(400, "No owned research queries to attach")

    matter.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "matter_id": str(matter.id),
        "title": matter.title,
        "attached_count": attached,
    }


@router.post("/")
async def create_matter(
    body: MatterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    matter = Matter(
        user_id=current_user.id,
        title=body.title,
        client_name=body.client_name,
        visa_type=body.visa_type,
        description=body.description,
    )
    db.add(matter)
    await db.commit()
    await db.refresh(matter)
    return {"id": str(matter.id), "title": matter.title}


@router.patch("/{matter_id}")
async def update_matter(
    matter_id: UUID,
    body: MatterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Matter).where(Matter.id == matter_id, Matter.user_id == current_user.id)
    )
    matter = result.scalars().first()
    if not matter:
        raise HTTPException(404, "Matter not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(matter, field, value)
    matter.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Updated"}


@router.delete("/{matter_id}")
async def delete_matter(
    matter_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Matter).where(Matter.id == matter_id, Matter.user_id == current_user.id)
    )
    matter = result.scalars().first()
    if not matter:
        raise HTTPException(404, "Matter not found")
    await db.execute(
        update(ChatQueryMeta)
        .where(ChatQueryMeta.matter_id == matter.id)
        .values(matter_id=None)
    )
    await db.delete(matter)
    await db.commit()
    return {"message": "Deleted"}
