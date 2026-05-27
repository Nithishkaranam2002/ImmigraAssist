import asyncio
import json
from celery import Task
from sqlalchemy import select, func
from app.tasks.celery_app import celery_app
from app.db.postgres import AsyncSessionLocal
from app.db.models.feedback import Feedback
from app.db.models.audit_log import AuditLog
from app.utils.logger import logger


class AsyncTask(Task):
    """Base task with async event loop management."""
    _loop = None

    @property
    def loop(self):
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop


@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="app.tasks.feedback_task.process_feedback_task",
)
def process_feedback_task(self):
    """
    Scheduled task — runs every 24 hours.

    Analyzes feedback patterns to surface insights:
    - Overall satisfaction rate
    - Which visa types get most negative feedback
    - Average response time trends
    - Queries with consistently negative feedback

    Logs insights so admins can review and improve retrieval.
    """
    logger.info("Feedback processing task started")

    async def _run():
        async with AsyncSessionLocal() as db:
            try:
                insights = {}

                # ── Overall satisfaction ───────────────────────────────
                total_result = await db.execute(
                    select(func.count(Feedback.id))
                )
                total_feedback = total_result.scalar() or 0

                positive_result = await db.execute(
                    select(func.count(Feedback.id))
                    .where(Feedback.is_positive == True)
                )
                positive_count = positive_result.scalar() or 0

                negative_count = total_feedback - positive_count
                satisfaction_rate = (
                    round(positive_count / total_feedback * 100, 1)
                    if total_feedback > 0 else 0
                )

                insights["overall"] = {
                    "total_feedback": total_feedback,
                    "positive": positive_count,
                    "negative": negative_count,
                    "satisfaction_rate_percent": satisfaction_rate,
                }

                # ── Visa type breakdown ────────────────────────────────
                visa_result = await db.execute(
                    select(
                        AuditLog.visa_type_detected,
                        func.count(Feedback.id).label("total"),
                        func.sum(
                            func.cast(Feedback.is_positive, db.bind.dialect.name == "postgresql" and "integer" or "INTEGER")
                        ).label("positive"),
                    )
                    .join(AuditLog, Feedback.audit_log_id == AuditLog.id)
                    .group_by(AuditLog.visa_type_detected)
                )
                visa_rows = visa_result.fetchall()

                visa_breakdown = {}
                for row in visa_rows:
                    visa_type = row[0] or "unknown"
                    total = row[1] or 0
                    pos = row[2] or 0
                    visa_breakdown[visa_type] = {
                        "total": total,
                        "positive": pos,
                        "negative": total - pos,
                        "satisfaction_rate": (
                            round(pos / total * 100, 1)
                            if total > 0 else 0
                        ),
                    }

                insights["by_visa_type"] = visa_breakdown

                # ── Avg response time ──────────────────────────────────
                avg_time_result = await db.execute(
                    select(func.avg(AuditLog.response_time_ms))
                )
                avg_response_time = avg_time_result.scalar()

                insights["performance"] = {
                    "avg_response_time_ms": (
                        round(avg_response_time, 0)
                        if avg_response_time else None
                    ),
                }

                # ── Queries with negative feedback ─────────────────────
                negative_queries_result = await db.execute(
                    select(AuditLog.query, AuditLog.visa_type_detected)
                    .join(Feedback, Feedback.audit_log_id == AuditLog.id)
                    .where(Feedback.is_positive == False)
                    .order_by(AuditLog.created_at.desc())
                    .limit(10)
                )
                negative_queries = [
                    {
                        "query": row[0][:100],
                        "visa_type": row[1],
                    }
                    for row in negative_queries_result.fetchall()
                ]

                insights["recent_negative_queries"] = negative_queries

                # ── Log the full insights report ───────────────────────
                logger.info(
                    f"Feedback insights report:\n"
                    f"{json.dumps(insights, indent=2)}"
                )

                # flag low satisfaction visa types
                for visa_type, stats in visa_breakdown.items():
                    if (
                        stats["total"] >= 5
                        and stats["satisfaction_rate"] < 60
                    ):
                        logger.warning(
                            f"LOW SATISFACTION ALERT — "
                            f"visa type '{visa_type}': "
                            f"{stats['satisfaction_rate']}% satisfaction "
                            f"({stats['total']} responses)"
                        )

                return insights

            except Exception as e:
                logger.error(f"Feedback processing failed: {e}")
                raise

    return self.loop.run_until_complete(_run())