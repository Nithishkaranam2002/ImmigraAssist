import os
from dotenv import load_dotenv

load_dotenv()

# ── LangSmith tracing — must be set BEFORE any other imports ───────────
os.environ["LANGSMITH_TRACING"] = os.getenv("LANGSMITH_TRACING", "true")
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "immigraassist")

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

    logger.info(f"All systems ready. {settings.APP_NAME} is running.")
    yield

    # ── Shutdown ───────────────────────────────────────────────────────
    logger.info("Shutting down...")
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(users.router, prefix="/api/v1", tags=["users"])
app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
app.include_router(invites.router, prefix="/api/v1", tags=["invites"])
app.include_router(cases.router, prefix="/api/v1", tags=["cases"])


@app.get("/health")
async def health():
    return {"status": "healthy"}