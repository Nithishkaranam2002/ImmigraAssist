import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from datetime import datetime, timezone, timedelta
from app.db.postgres import get_db
from app.db.models.user import User, UserRole
from app.db.models.audit_log import AuditLog
from app.db.models.chat_query_meta import ChatQueryMeta
from app.db.models.review_item import ReviewItem
from app.db.models.policy_alert import PolicyAlert
from app.db.models.feedback import Feedback
from app.api.v1.dependencies import get_current_user, require_role
from app.config import settings

router = APIRouter(prefix="/platform", tags=["platform"])


class IntegrationQuery(BaseModel):
    query: str
    query_mode: str = "standard"


async def verify_integration_key(x_api_key: Optional[str] = Header(None)):
    if not settings.INTEGRATION_API_KEY:
        raise HTTPException(501, "Integration API not configured")
    if x_api_key != settings.INTEGRATION_API_KEY:
        raise HTTPException(401, "Invalid API key")
    return True

VISA_RESEARCH = {
    "h1b": {
        "title": "H-1B Specialty Occupation",
        "description": "Temporary work visa for specialty occupations requiring a bachelor's degree or higher.",
        "suggestions": [
            "What are H-1B specialty occupation requirements?",
            "Explain AC21 portability for H1B holders",
            "Compare H1B vs L1 for intracompany transfer",
        ],
        "forms": ["I-129", "I-797"],
    },
    "h4_ead": {
        "title": "H-4 Employment Authorization",
        "description": "Work authorization for certain H-4 dependent spouses of H-1B holders.",
        "suggestions": [
            "What are the requirements for H4 EAD eligibility?",
            "When can H-4 spouses apply for EAD?",
        ],
        "forms": ["I-765", "I-539"],
    },
    "asylum": {
        "title": "Asylum & Humanitarian Protection",
        "description": "Protection for individuals persecuted or fearing persecution in their home country.",
        "suggestions": [
            "What documents are needed for an asylum application?",
            "Explain credible fear interview process",
        ],
        "forms": ["I-589", "I-765"],
    },
    "green_card": {
        "title": "Green Card / Adjustment of Status",
        "description": "Lawful permanent residence through family, employment, or other pathways.",
        "suggestions": [
            "What is the PERM labor certification process?",
            "Explain adjustment of status vs consular processing",
        ],
        "forms": ["I-485", "I-140", "I-693"],
    },
    "o1": {
        "title": "O-1 Extraordinary Ability",
        "description": "Visa for individuals with extraordinary ability in sciences, arts, education, business, or athletics.",
        "suggestions": ["What evidence is required for O-1 extraordinary ability?"],
        "forms": ["I-129"],
    },
}


@router.post("/integration/query")
async def integration_query(
    body: IntegrationQuery,
    _: bool = Depends(verify_integration_key),
):
    """Webhook-style query endpoint for external integrations (Clio, MyCase, etc.)."""
    return {
        "status": "accepted",
        "message": "Use POST /api/v1/chat/query with a user JWT for full RAG pipeline.",
        "query": body.query,
        "query_mode": body.query_mode,
        "docs": "https://github.com/Nithishkaranam2002/ImmigraAssist",
    }


@router.get("/research/{visa_type}")
async def visa_research_hub(visa_type: str):
    data = VISA_RESEARCH.get(visa_type.lower())
    if not data:
        raise HTTPException(404, "Visa type not found")
    return {"visa_type": visa_type, **data}


@router.get("/research")
async def list_research_hubs():
    return [{"id": k, "title": v["title"]} for k, v in VISA_RESEARCH.items()]


@router.get("/history")
async def query_history(
    limit: int = 30,
    matter_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(AuditLog, ChatQueryMeta)
        .outerjoin(ChatQueryMeta, ChatQueryMeta.audit_log_id == AuditLog.id)
        .where(AuditLog.user_id == current_user.id)
    )
    if matter_id:
        stmt = stmt.where(ChatQueryMeta.matter_id == matter_id)
    result = await db.execute(
        stmt.order_by(AuditLog.created_at.desc()).limit(limit)
    )
    rows = result.all()
    return [
        {
            "id": str(log.id),
            "query": log.query,
            "answer_preview": (log.answer or "")[:200],
            "visa_type": log.visa_type_detected,
            "response_time_ms": log.response_time_ms,
            "confidence_level": meta.confidence_level if meta else None,
            "matter_id": str(meta.matter_id) if meta and meta.matter_id else None,
            "created_at": str(log.created_at),
        }
        for log, meta in rows
    ]


@router.get("/history/{audit_id}")
async def get_history_item(
    audit_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AuditLog).where(AuditLog.id == audit_id, AuditLog.user_id == current_user.id)
    )
    log = result.scalars().first()
    if not log:
        raise HTTPException(404, "Not found")
    meta_result = await db.execute(
        select(ChatQueryMeta).where(ChatQueryMeta.audit_log_id == log.id)
    )
    meta = meta_result.scalars().first()
    return {
        "id": str(log.id),
        "query": log.query,
        "answer": log.answer,
        "visa_type": log.visa_type_detected,
        "response_time_ms": log.response_time_ms,
        "confidence_score": meta.confidence_score if meta else None,
        "confidence_level": meta.confidence_level if meta else None,
        "next_steps": json.loads(meta.next_steps) if meta and meta.next_steps else [],
        "risks": json.loads(meta.risks) if meta and meta.risks else [],
        "related_forms": json.loads(meta.related_forms) if meta and meta.related_forms else [],
        "created_at": str(log.created_at),
    }


@router.get("/alerts")
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    result = await db.execute(
        select(PolicyAlert).order_by(PolicyAlert.created_at.desc()).limit(50)
    )
    alerts = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "title": a.title,
            "url": a.url,
            "source_type": a.source_type,
            "summary": a.summary,
            "is_read": a.is_read,
            "created_at": str(a.created_at),
        }
        for a in alerts
    ]


@router.patch("/alerts/{alert_id}/read")
async def mark_alert_read(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    result = await db.execute(select(PolicyAlert).where(PolicyAlert.id == alert_id))
    alert = result.scalars().first()
    if alert:
        alert.is_read = True
        await db.commit()
    return {"message": "ok"}


@router.get("/reviews")
async def list_reviews(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    result = await db.execute(
        select(ReviewItem, AuditLog)
        .join(AuditLog, AuditLog.id == ReviewItem.audit_log_id)
        .where(ReviewItem.status == "pending")
        .order_by(ReviewItem.created_at.desc())
        .limit(50)
    )
    return [
        {
            "id": str(item.id),
            "audit_log_id": str(item.audit_log_id),
            "query": log.query,
            "answer_preview": (log.answer or "")[:300],
            "status": item.status,
            "created_at": str(item.created_at),
        }
        for item, log in result.all()
    ]


class ReviewAction(BaseModel):
    status: str
    notes: Optional[str] = None


@router.patch("/reviews/{review_id}")
async def update_review(
    review_id: UUID,
    body: ReviewAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ATTORNEY)),
):
    result = await db.execute(select(ReviewItem).where(ReviewItem.id == review_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(404, "Review not found")
    item.status = body.status
    item.reviewer_notes = body.notes
    item.reviewed_by = current_user.id
    item.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Updated"}


def _percentile(values: list[int], p: float) -> int:
    if not values:
        return 0
    vals = sorted(values)
    k = (len(vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    return int(vals[f] + (vals[c] - vals[f]) * (k - f))


def _fill_daily_buckets(rows: list, days: int = 14) -> list[dict]:
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    buckets = {
        (today - timedelta(days=days - 1 - i)).date().isoformat(): 0 for i in range(days)
    }
    for day_val, count in rows:
        if day_val is None:
            continue
        key = day_val.date().isoformat() if hasattr(day_val, "date") else str(day_val)[:10]
        if key in buckets:
            buckets[key] = int(count)
    return [{"date": d, "count": buckets[d]} for d in sorted(buckets)]


def _fill_hourly_buckets(rows: list, hours: int = 24) -> list[dict]:
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    buckets = {
        (now - timedelta(hours=hours - 1 - i)).strftime("%Y-%m-%dT%H:00"): 0
        for i in range(hours)
    }
    for hour_val, count in rows:
        if hour_val is None:
            continue
        key = hour_val.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:00")
        if key in buckets:
            buckets[key] = int(count)
    return [{"hour": h, "count": buckets[h]} for h in sorted(buckets)]


@router.get("/eval-metrics")
async def eval_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hour_ago = now - timedelta(hours=1)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    total_q = await db.execute(select(func.count(AuditLog.id)))
    total_queries = total_q.scalar() or 0

    today_q = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.created_at >= day_start)
    )
    last_24h_q = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.created_at >= day_ago)
    )
    last_hour_q = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.created_at >= hour_ago)
    )

    avg_time = await db.execute(select(func.avg(AuditLog.response_time_ms)))
    avg_ms = int(avg_time.scalar() or 0)

    latency_rows = await db.execute(
        select(AuditLog.response_time_ms).where(AuditLog.response_time_ms.isnot(None))
    )
    latency_vals = [r[0] for r in latency_rows.fetchall() if r[0] is not None]

    fb = await db.execute(
        select(Feedback.is_positive, func.count(Feedback.id)).group_by(Feedback.is_positive)
    )
    pos = neg = 0
    for is_pos, cnt in fb.fetchall():
        if is_pos:
            pos = cnt
        else:
            neg = cnt

    conf = await db.execute(
        select(ChatQueryMeta.confidence_level, func.count(ChatQueryMeta.id))
        .group_by(ChatQueryMeta.confidence_level)
    )
    confidence_dist = {row[0]: row[1] for row in conf.fetchall() if row[0]}

    avg_conf = await db.execute(select(func.avg(ChatQueryMeta.confidence_score)))
    avg_confidence_score = round(float(avg_conf.scalar() or 0), 3)

    needs_review_result = await db.execute(
        select(func.count(ChatQueryMeta.id)).where(ChatQueryMeta.needs_review.is_(True))
    )

    cache_total = await db.execute(select(func.count(ChatQueryMeta.id)))
    cache_hits_result = await db.execute(
        select(func.count(ChatQueryMeta.id)).where(ChatQueryMeta.from_cache.is_(True))
    )
    cache_total_n = cache_total.scalar() or 0
    cache_hits = cache_hits_result.scalar() or 0

    mode_result = await db.execute(
        select(ChatQueryMeta.query_mode, func.count(ChatQueryMeta.id))
        .group_by(ChatQueryMeta.query_mode)
    )
    query_mode_distribution = {row[0] or "standard": row[1] for row in mode_result.fetchall()}

    visa_result = await db.execute(
        select(AuditLog.visa_type_detected, func.count(AuditLog.id))
        .where(AuditLog.visa_type_detected.isnot(None))
        .group_by(AuditLog.visa_type_detected)
        .order_by(func.count(AuditLog.id).desc())
        .limit(8)
    )
    visa_type_distribution = {
        (row[0] or "unknown").upper(): row[1] for row in visa_result.fetchall()
    }

    review_status_result = await db.execute(
        select(ReviewItem.status, func.count(ReviewItem.id)).group_by(ReviewItem.status)
    )
    review_status = {row[0]: row[1] for row in review_status_result.fetchall()}

    pending = await db.execute(
        select(func.count(ReviewItem.id)).where(ReviewItem.status == "pending")
    )

    daily_rows = await db.execute(
        select(
            func.date_trunc("day", AuditLog.created_at).label("day"),
            func.count(AuditLog.id),
        )
        .where(AuditLog.created_at >= two_weeks_ago)
        .group_by("day")
        .order_by("day")
    )

    hourly_rows = await db.execute(
        select(
            func.date_trunc("hour", AuditLog.created_at).label("hour"),
            func.count(AuditLog.id),
        )
        .where(AuditLog.created_at >= day_ago)
        .group_by("hour")
        .order_by("hour")
    )

    feedback_trend_rows = await db.execute(
        select(
            func.date_trunc("day", Feedback.created_at).label("day"),
            Feedback.is_positive,
            func.count(Feedback.id),
        )
        .where(Feedback.created_at >= week_ago)
        .group_by("day", Feedback.is_positive)
        .order_by("day")
    )
    fb_by_day: dict[str, dict[str, int]] = {}
    for day_val, is_positive, cnt in feedback_trend_rows.fetchall():
        if day_val is None:
            continue
        key = day_val.date().isoformat()
        if key not in fb_by_day:
            fb_by_day[key] = {"positive": 0, "negative": 0}
        if is_positive:
            fb_by_day[key]["positive"] = int(cnt)
        else:
            fb_by_day[key]["negative"] = int(cnt)

    feedback_trend = []
    for i in range(7):
        d = (now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=6 - i)).date().isoformat()
        entry = fb_by_day.get(d, {"positive": 0, "negative": 0})
        feedback_trend.append({"date": d, **entry})

    recent_rows = await db.execute(
        select(AuditLog, ChatQueryMeta)
        .outerjoin(ChatQueryMeta, ChatQueryMeta.audit_log_id == AuditLog.id)
        .order_by(AuditLog.created_at.desc())
        .limit(8)
    )
    recent_activity = [
        {
            "id": str(log.id),
            "query": (log.query or "")[:120],
            "visa_type": log.visa_type_detected,
            "confidence_level": meta.confidence_level if meta else None,
            "response_time_ms": log.response_time_ms or 0,
            "from_cache": bool(meta.from_cache) if meta else False,
            "created_at": str(log.created_at),
        }
        for log, meta in recent_rows.all()
    ]

    return {
        "total_queries": total_queries,
        "queries_today": today_q.scalar() or 0,
        "queries_last_24h": last_24h_q.scalar() or 0,
        "queries_last_hour": last_hour_q.scalar() or 0,
        "avg_response_time_ms": avg_ms,
        "latency_p50_ms": _percentile(latency_vals, 0.5),
        "latency_p95_ms": _percentile(latency_vals, 0.95),
        "feedback_positive": pos,
        "feedback_negative": neg,
        "satisfaction_rate": round(pos / (pos + neg) * 100, 1) if (pos + neg) else None,
        "confidence_distribution": confidence_dist,
        "avg_confidence_score": avg_confidence_score,
        "needs_review_count": needs_review_result.scalar() or 0,
        "cache_hits": cache_hits,
        "cache_hit_rate": round(cache_hits / cache_total_n * 100, 1) if cache_total_n else 0,
        "query_mode_distribution": query_mode_distribution,
        "visa_type_distribution": visa_type_distribution,
        "review_status": review_status,
        "pending_reviews": pending.scalar() or 0,
        "daily_volume": _fill_daily_buckets(daily_rows.fetchall()),
        "hourly_activity": _fill_hourly_buckets(hourly_rows.fetchall()),
        "feedback_trend": feedback_trend,
        "recent_activity": recent_activity,
        "updated_at": now.isoformat(),
    }
