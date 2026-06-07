from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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


@router.get("/")
async def list_matters(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Matter)
        .where(Matter.user_id == current_user.id)
        .order_by(Matter.updated_at.desc().nullslast(), Matter.created_at.desc())
    )
    matters = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "title": m.title,
            "client_name": m.client_name,
            "visa_type": m.visa_type,
            "description": m.description,
            "status": m.status,
            "created_at": str(m.created_at),
        }
        for m in matters
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
    await db.delete(matter)
    await db.commit()
    return {"message": "Deleted"}
