import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.postgres import create_tables, AsyncSessionLocal
# import all models so SQLAlchemy mapper initializes before create_tables()
from app.db.models.user import User  # noqa
from app.db.models.document import Document  # noqa
from app.db.models.chunk import Chunk  # noqa
from app.db.models.case import Case  # noqa
from app.db.models.audit_log import AuditLog  # noqa
from app.db.models.feedback import Feedback  # noqa
from app.db.models.section_map import SectionMap  # noqa
from app.db.models.scrape_record import ScrapeRecord  # noqa
from app.db.models.invite import Invite  # noqa
from app.db.models.matter import Matter  # noqa
from app.db.models.chat_query_meta import ChatQueryMeta  # noqa
from app.db.models.review_item import ReviewItem  # noqa
from app.db.models.policy_alert import PolicyAlert  # noqa
from app.db.milvus import setup_collections
from app.db.redis import get_redis, close_redis
from app.db.seeder import seed_super_admin
from app.api.v1.routes import auth, chat, documents, users, feedback, admin, invites, cases, matters, platform
from app.config import settings
from app.utils.logger import logger
from app.middleware.rate_limit import RateLimitMiddleware

# LangSmith tracing — only when API key is configured
if os.getenv("LANGSMITH_API_KEY") or settings.LANGCHAIN_API_KEY:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", settings.LANGCHAIN_API_KEY)
    os.environ["LANGSMITH_PROJECT"] = settings.LANGCHAIN_PROJECT


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
    description="AI-powered immigration legal research API with RAG pipeline, hybrid retrieval, and audit logging.",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.CORS_ORIGINS.strip() != "*",
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
app.include_router(matters.router, prefix="/api/v1", tags=["matters"])
app.include_router(platform.router, prefix="/api/v1", tags=["platform"])


@app.get("/health")
async def health():
    return {"status": "healthy"}