from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.user import User, UserRole
from app.core.security import hash_password
from app.config import settings
from app.utils.logger import logger


async def seed_super_admin(db: AsyncSession):
    """
    On first startup if no users exist,
    create the super admin from .env settings.
    """
    result = await db.execute(select(User).limit(1))
    existing = result.scalars().first()

    if existing:
        logger.info("Users already exist — skipping super admin seed")
        return

    logger.info(f"No users found — seeding super admin: {settings.ADMIN_EMAIL}")

    admin = User(
        full_name=settings.ADMIN_NAME,
        email=settings.ADMIN_EMAIL,
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        role=UserRole.SUPER_ADMIN,
        designation=settings.ADMIN_DESIGNATION,
        is_active=True,
        is_verified=True,
    )
    db.add(admin)
    await db.commit()
    logger.info(f"Super admin created: {settings.ADMIN_EMAIL}")