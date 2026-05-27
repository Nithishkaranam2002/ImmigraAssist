from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.postgres import create_tables, AsyncSessionLocal
from app.db.models import scrape_record  # noqa - ensures table is created
from app.db.models import invite  # noqa - ensures table is created
from app.db.milvus import setup_collections
from app.db.redis import get_redis, close_redis
from app.db.seeder import seed_super_admin
from app.api.v1.routes import auth, chat, documents, users, feedback, admin, invites, cases
from app.config import settings
from app.utils.logger import logger
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    os.makedirs("logs", exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    logger.info("Setting up PostgreSQL tables...")
    await create_tables()

    logger.info("Seeding super admin if needed...")
    async with AsyncSessionLocal() as db:
        await seed_super_admin(db)

    logger.info("Setting up Milvus collections...")
    setup_collections()

    logger.info("Connecting to Redis...")
    await get_redis()

    logger.info("All systems ready. ImmigraAssist is running.")

    yield  # app is running

    # ── Shutdown ───────────────────────────────────────────────────────
    logger.info("Shutting down ImmigraAssist...")
    await close_redis()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered immigration legal research assistant",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ─────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(invites.router, prefix="/api/v1")
app.include_router(cases.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "tagline": "From Policies to Precedents, Instantly.",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}