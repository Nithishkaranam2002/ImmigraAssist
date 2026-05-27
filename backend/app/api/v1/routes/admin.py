from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.postgres import get_db
from app.db.models.user import User, UserRole
from app.db.models.document import Document, DocumentStatus
from app.db.models.chunk import Chunk
from app.db.models.audit_log import AuditLog
from app.db.models.feedback import Feedback
from app.api.v1.dependencies import require_role
from app.db.milvus import get_laws_collection, get_cases_collection
from app.utils.logger import logger

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health")
async def system_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Check health of all system components.
    Returns status of PostgreSQL, Milvus, and Redis.
    """
    health = {
        "postgresql": "unknown",
        "milvus_laws": "unknown",
        "milvus_cases": "unknown",
        "overall": "unknown",
    }

    # check PostgreSQL
    try:
        await db.execute(select(func.now()))
        health["postgresql"] = "healthy"
    except Exception as e:
        health["postgresql"] = f"unhealthy: {str(e)}"

    # check Milvus collections
    try:
        laws_col = get_laws_collection()
        health["milvus_laws"] = f"healthy ({laws_col.num_entities} chunks)"
    except Exception as e:
        health["milvus_laws"] = f"unhealthy: {str(e)}"

    try:
        cases_col = get_cases_collection()
        health["milvus_cases"] = f"healthy ({cases_col.num_entities} chunks)"
    except Exception as e:
        health["milvus_cases"] = f"unhealthy: {str(e)}"

    # overall status
    all_healthy = all(
        "healthy" in v for v in health.values()
        if v != "unknown"
    )
    health["overall"] = "healthy" if all_healthy else "degraded"

    return health


@router.get("/stats")
async def system_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    System-wide statistics for admin dashboard.
    """
    # user counts
    user_result = await db.execute(select(func.count(User.id)))
    total_users = user_result.scalar()

    # document counts by status
    doc_result = await db.execute(
        select(Document.status, func.count(Document.id))
        .group_by(Document.status)
    )
    doc_stats = {row[0].value: row[1] for row in doc_result.fetchall()}

    # chunk count
    chunk_result = await db.execute(select(func.count(Chunk.id)))
    total_chunks = chunk_result.scalar()

    # query count
    query_result = await db.execute(select(func.count(AuditLog.id)))
    total_queries = query_result.scalar()

    # feedback stats
    feedback_result = await db.execute(
        select(Feedback.is_positive, func.count(Feedback.id))
        .group_by(Feedback.is_positive)
    )
    feedback_rows = feedback_result.fetchall()
    positive = sum(r[1] for r in feedback_rows if r[0] is True)
    negative = sum(r[1] for r in feedback_rows if r[0] is False)

    return {
        "total_users": total_users,
        "documents": doc_stats,
        "total_chunks_indexed": total_chunks,
        "total_queries": total_queries,
        "feedback": {
            "positive": positive,
            "negative": negative,
            "satisfaction_rate": (
                round(positive / (positive + negative) * 100, 1)
                if (positive + negative) > 0 else None
            ),
        },
    }


@router.get("/audit-logs")
async def list_audit_logs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """List recent audit logs. Admin only."""
    result = await db.execute(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "user_id": str(log.user_id),
            "query": log.query[:100] + "..." if len(log.query) > 100 else log.query,
            "visa_type_detected": log.visa_type_detected,
            "response_time_ms": log.response_time_ms,
            "token_count": log.token_count,
            "created_at": str(log.created_at),
        }
        for log in logs
    ]

@router.post("/scrape/trigger")
async def trigger_scraper(
    scrape_policy: bool = True,
    scrape_news: bool = True,
    scrape_bia: bool = True,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Manually trigger the scraper pipeline.
    Admin only. Runs as background Celery task.
    """
    from app.tasks.scraper_task import run_scrapers_task
    task = run_scrapers_task.delay(
        scrape_policy=scrape_policy,
        scrape_news=scrape_news,
        scrape_bia=scrape_bia,
    )
    logger.info(
        f"Scraper manually triggered by {current_user.email} "
        f"— task_id: {task.id}"
    )
    return {
        "message": "Scraper started",
        "task_id": task.id,
        "scrape_policy": scrape_policy,
        "scrape_news": scrape_news,
        "scrape_bia": scrape_bia,
    }
