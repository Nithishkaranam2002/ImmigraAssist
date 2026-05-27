from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


# base class all models inherit from
class Base(DeclarativeBase):
    pass


# async engine — non blocking database connection
engine = create_async_engine(
    settings.POSTGRES_URL,
    echo=settings.DEBUG,        # logs SQL queries in debug mode
    pool_size=10,               # max 10 persistent connections
    max_overflow=20,            # 20 extra connections under heavy load
    pool_pre_ping=True,         # check connection is alive before using
)

# session factory — creates new sessions on demand
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,     # don't expire objects after commit
)


async def get_db():
    """
    Dependency injected into every API route that needs DB access.
    Opens a session, yields it, closes it when request is done.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """
    Creates all tables on startup if they don't exist.
    Called from main.py on app startup.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)