import time
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from app.db.postgres import session_scope
from app.db.models.user import User
from app.db.models.audit_log import AuditLog
from app.db.models.chat_query_meta import ChatQueryMeta
from app.db.models.review_item import ReviewItem
from app.api.v1.dependencies import get_current_user
from app.guardrails.content_moderator import ContentModerator
from app.guardrails.pii_detector import get_pii_detector
from app.guardrails.output_sanitizer import OutputSanitizer
from app.retrieval.metadata_filter import MetadataFilter
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.reranker import Reranker
from app.retrieval.clustering import CaseClustering
from app.retrieval.context_builder import ContextBuilder
from app.llm.prompt_builder import PromptBuilder
from app.llm.gpt_client import GPTClient, GPTResponse
from app.llm.response_parser import ResponseParser
from app.scrapers.courtlistener_scraper import CourtListenerScraper
from app.services.confidence import compute_confidence
from app.services.answer_quality import assess_and_enhance
from app.services.form_mapper import get_forms_for_visa
from app.services.query_cache import get_cached_response, set_cached_response
from app.config import settings
from app.utils.logger import logger

router = APIRouter(prefix="/chat", tags=["chat"])

moderator = ContentModerator()
pii_detector = get_pii_detector()
output_sanitizer = OutputSanitizer()
metadata_filter = MetadataFilter()
hybrid_retriever = HybridRetriever()
reranker = Reranker()
clustering = CaseClustering()
context_builder = ContextBuilder()
prompt_builder = PromptBuilder()
gpt_client = GPTClient()
response_parser = ResponseParser()


class QueryRequest(BaseModel):
    query: str
    stream: bool = False
    matter_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    query_mode: str = "standard"


class DocQueryRequest(BaseModel):
    document_text: str = Field(..., max_length=50000)
    query: str
    matter_id: Optional[UUID] = None
    session_id: Optional[UUID] = None


class CourtCase(BaseModel):
    case_name: str
    case_id: str
    court: str
    date_decided: Optional[str]
    citation: Optional[str]
    summary: Optional[str]
    courtlistener_url: str
    visa_types: list[str]
    outcome: Optional[str]
    relevance_score: float


class QueryResponse(BaseModel):
    answer: str
    cited_laws: list[str]
    cited_cases: list[str]
    court_cases: list[CourtCase]
    important_notes: list[str]
    next_steps: list[str] = []
    risks: list[str] = []
    related_forms: list[str] = []
    audit_log_id: str
    response_time_ms: int
    visa_type_detected: Optional[str]
    confidence_score: Optional[float] = None
    confidence_level: Optional[str] = None
    confidence_label: Optional[str] = None
    from_cache: bool = False
    session_id: Optional[str] = None
    matter_id: Optional[str] = None


def _court_cases_response(court_cases) -> list[CourtCase]:
    return [
        CourtCase(
            case_name=c.case_name,
            case_id=c.case_id,
            court=c.court_name,
            date_decided=c.date_decided,
            citation=c.citation,
            summary=c.summary,
            courtlistener_url=c.courtlistener_url,
            visa_types=c.visa_types,
            outcome=c.outcome,
            relevance_score=c.relevance_score,
        )
        for c in court_cases
    ]


async def _get_session_context(
    db: AsyncSession,
    session_id: UUID,
    user_id: UUID,
    limit: int = 3,
) -> str:
    result = await db.execute(
        select(AuditLog)
        .join(ChatQueryMeta, ChatQueryMeta.audit_log_id == AuditLog.id)
        .where(
            ChatQueryMeta.session_id == session_id,
            AuditLog.user_id == user_id,
        )
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    parts = []
    for log in reversed(logs):
        parts.append(f"Q: {log.query}\nA: {(log.answer or '')[:500]}")
    return "\n\n".join(parts)


async def _save_query_meta(
    db: AsyncSession,
    audit_log_id: UUID,
    *,
    matter_id: Optional[UUID],
    session_id: Optional[UUID],
    confidence,
    parsed,
    query_mode: str,
    from_cache: bool,
    related_forms: list[str],
) -> None:
    meta = ChatQueryMeta(
        audit_log_id=audit_log_id,
        matter_id=matter_id,
        session_id=session_id,
        confidence_score=confidence.score,
        confidence_level=confidence.level,
        next_steps=json.dumps(parsed.next_steps),
        risks=json.dumps(parsed.risks),
        related_forms=json.dumps(related_forms),
        query_mode=query_mode,
        from_cache=from_cache,
        needs_review=confidence.needs_review,
    )
    db.add(meta)
    if confidence.needs_review:
        db.add(ReviewItem(audit_log_id=audit_log_id, status="pending"))


@router.post("/query", response_model=QueryResponse)
async def query(
    body: QueryRequest,
    current_user: User = Depends(get_current_user),
):
    start_time = time.time()
    session_id = body.session_id or uuid.uuid4()
    query_mode = body.query_mode if body.query_mode in ("standard", "compare") else "standard"

    logger.info(f"Query from {current_user.email}: '{body.query[:80]}...' mode={query_mode}")

    mod_result = moderator.moderate(body.query)
    if not mod_result.is_safe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=mod_result.reason)

    pii_result = pii_detector.detect_and_redact(body.query)
    clean_query = pii_result.redacted_text

    if not body.stream:
        cached = await get_cached_response(clean_query, query_mode)
        if cached:
            cached["from_cache"] = True
            cached["session_id"] = str(session_id)
            if body.matter_id:
                cached["matter_id"] = str(body.matter_id)
            return QueryResponse(**cached)

    if body.stream:
        return StreamingResponse(
            _stream_pipeline(
                current_user=current_user,
                body=body,
                clean_query=clean_query,
                session_id=session_id,
                query_mode=query_mode,
                start_time=start_time,
            ),
            media_type="text/event-stream",
        )

    result = await _run_pipeline(
        current_user=current_user,
        raw_query=body.query,
        clean_query=clean_query,
        matter_id=body.matter_id,
        session_id=session_id,
        query_mode=query_mode,
        start_time=start_time,
        extra_context=None,
    )

    await set_cached_response(clean_query, result, query_mode)
    return QueryResponse(**result)


@router.post("/doc-query", response_model=QueryResponse)
async def doc_query(
    body: DocQueryRequest,
    current_user: User = Depends(get_current_user),
):
    """Ask questions about an uploaded client document (petition draft, etc.)."""
    start_time = time.time()
    session_id = body.session_id or uuid.uuid4()

    mod_result = moderator.moderate(body.query)
    if not mod_result.is_safe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=mod_result.reason)

    doc_text = body.document_text[:30000]
    extra = f"## CLIENT DOCUMENT (for review)\n{doc_text}"

    pii_result = pii_detector.detect_and_redact(body.query)
    clean_query = pii_result.redacted_text

    result = await _run_pipeline(
        current_user=current_user,
        raw_query=body.query,
        clean_query=clean_query,
        matter_id=body.matter_id,
        session_id=session_id,
        query_mode="standard",
        start_time=start_time,
        extra_context=extra,
    )
    return QueryResponse(**result)


async def _run_pipeline(
    *,
    current_user: User,
    raw_query: str,
    clean_query: str,
    matter_id: Optional[UUID],
    session_id: UUID,
    query_mode: str,
    start_time: float,
    extra_context: Optional[str],
) -> dict:
    async with session_scope() as db:
        filter_context = await metadata_filter.build_filter_context(db=db, query=clean_query)
        session_context = ""
        if session_id:
            session_context = await _get_session_context(db, session_id, current_user.id)

    law_chunks, case_chunks, court_cases = await _retrieve_all(
        query=clean_query,
        filter_context=filter_context,
        visa_type=filter_context.visa_type,
    )

    law_chunks = await reranker.rerank(query=clean_query, chunks=law_chunks)
    case_chunks = await reranker.rerank(query=clean_query, chunks=case_chunks)
    case_chunks = await clustering.cluster_and_select(chunks=case_chunks)

    async with session_scope() as db:
        context = await context_builder.build(
            db=db,
            law_chunks=law_chunks,
            case_chunks=case_chunks,
            court_cases=court_cases,
        )

    if extra_context:
        context.context_text = extra_context + "\n\n" + context.context_text

    if session_context:
        context.context_text = (
            f"## PREVIOUS CONVERSATION\n{session_context}\n\n" + context.context_text
        )

    prompt = prompt_builder.build(
        query=clean_query,
        context=context,
        visa_type=filter_context.visa_type,
        query_mode=query_mode,
    )

    gpt_response = await gpt_client.complete(prompt)

    async with session_scope() as db:
        return await _finalize_response(
            db=db,
            current_user=current_user,
            raw_query=raw_query,
            context=context,
            gpt_response=gpt_response,
            law_chunks=law_chunks,
            case_chunks=case_chunks,
            court_cases=court_cases,
            filter_context=filter_context,
            matter_id=matter_id,
            session_id=session_id,
            query_mode=query_mode,
            start_time=start_time,
            from_cache=False,
        )


async def _finalize_response(
    *,
    db: AsyncSession,
    current_user: User,
    raw_query: str,
    context,
    gpt_response: GPTResponse,
    law_chunks,
    case_chunks,
    court_cases,
    filter_context,
    matter_id: Optional[UUID],
    session_id: UUID,
    query_mode: str,
    start_time: float,
    from_cache: bool,
) -> dict:
    parsed = response_parser.parse(gpt_response)
    quality = assess_and_enhance(
        parsed=parsed,
        query=raw_query,
        visa_type=filter_context.visa_type,
        law_count=len(law_chunks),
        case_count=len(case_chunks),
        court_count=len(court_cases),
    )
    parsed = quality.parsed

    sanitized = output_sanitizer.sanitize(raw_answer=parsed.answer, context=context)

    confidence = compute_confidence(
        law_count=len(law_chunks),
        case_count=len(case_chunks),
        court_count=len(court_cases),
        is_well_formed=parsed.is_well_formed,
        completeness_score=quality.completeness_score,
        gap_count=len(quality.gaps),
    )

    form_list = list(parsed.related_forms or [])
    if filter_context.visa_type:
        for f in get_forms_for_visa(filter_context.visa_type):
            entry = f"{f['form']} — {f['name']}"
            if entry not in form_list:
                form_list.append(entry)

    response_time_ms = int((time.time() - start_time) * 1000)

    audit_log = AuditLog(
        user_id=current_user.id,
        query=raw_query,
        answer=sanitized.answer,
        retrieved_law_chunks=json.dumps([c.chunk_id for c in law_chunks]),
        retrieved_case_chunks=json.dumps([c.chunk_id for c in case_chunks]),
        visa_type_detected=filter_context.visa_type,
        response_time_ms=response_time_ms,
        token_count=gpt_response.total_tokens,
    )
    db.add(audit_log)
    await db.flush()

    await _save_query_meta(
        db,
        audit_log.id,
        matter_id=matter_id,
        session_id=session_id,
        confidence=confidence,
        parsed=parsed,
        query_mode=query_mode,
        from_cache=from_cache,
        related_forms=form_list,
    )
    await db.refresh(audit_log)

    court_resp = _court_cases_response(court_cases)

    return {
        "answer": sanitized.answer,
        "cited_laws": sanitized.law_citations,
        "cited_cases": sanitized.case_citations,
        "court_cases": [c.model_dump() for c in court_resp],
        "important_notes": parsed.important_notes,
        "next_steps": parsed.next_steps,
        "risks": parsed.risks,
        "related_forms": form_list,
        "audit_log_id": str(audit_log.id),
        "response_time_ms": response_time_ms,
        "visa_type_detected": filter_context.visa_type,
        "confidence_score": confidence.score,
        "confidence_level": confidence.level,
        "confidence_label": confidence.label,
        "from_cache": from_cache,
        "session_id": str(session_id),
        "matter_id": str(matter_id) if matter_id else None,
    }


async def _stream_pipeline(
    current_user, body, clean_query, session_id, query_mode, start_time
):
    try:
        async with session_scope() as db:
            filter_context = await metadata_filter.build_filter_context(db=db, query=clean_query)
            session_context = await _get_session_context(db, session_id, current_user.id)

        law_chunks, case_chunks, court_cases = await _retrieve_all(
            query=clean_query,
            filter_context=filter_context,
            visa_type=filter_context.visa_type,
        )

        law_chunks = await reranker.rerank(query=clean_query, chunks=law_chunks)
        case_chunks = await reranker.rerank(query=clean_query, chunks=case_chunks)
        case_chunks = await clustering.cluster_and_select(chunks=case_chunks)

        async with session_scope() as db:
            context = await context_builder.build(
                db=db,
                law_chunks=law_chunks,
                case_chunks=case_chunks,
                court_cases=court_cases,
            )

        if session_context:
            context.context_text = (
                f"## PREVIOUS CONVERSATION\n{session_context}\n\n" + context.context_text
            )

        prompt = prompt_builder.build(
            query=clean_query,
            context=context,
            visa_type=filter_context.visa_type,
            query_mode=query_mode,
        )

        full_content = ""
        async for chunk in gpt_client.complete_streaming(prompt):
            full_content += chunk
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

        gpt_response = GPTResponse(
            content=full_content,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            model=settings.OPENAI_MODEL,
            response_time_ms=0,
        )

        async with session_scope() as db:
            result = await _finalize_response(
                db=db,
                current_user=current_user,
                raw_query=body.query,
                context=context,
                gpt_response=gpt_response,
                law_chunks=law_chunks,
                case_chunks=case_chunks,
                court_cases=court_cases,
                filter_context=filter_context,
                matter_id=body.matter_id,
                session_id=session_id,
                query_mode=query_mode,
                start_time=start_time,
                from_cache=False,
            )

        yield f"data: {json.dumps({'type': 'done', **result})}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error(f"Stream pipeline error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


async def _retrieve_all(query, filter_context, visa_type) -> tuple:
    scraper = CourtListenerScraper()
    try:
        try:
            law_chunks, case_chunks = await hybrid_retriever.retrieve(
                query=query, filter_context=filter_context
            )
        except Exception as e:
            logger.error(f"Milvus retrieval failed: {e}")
            law_chunks, case_chunks = [], []

        try:
            court_cases = await scraper.search(
                query=query,
                visa_type=visa_type,
                max_results=settings.COURTLISTENER_MAX_RESULTS,
            )
        except Exception as e:
            logger.error(f"CourtListener search failed: {e}")
            court_cases = []

        return law_chunks, case_chunks, court_cases
    finally:
        await scraper.close()
