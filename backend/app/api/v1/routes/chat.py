import time
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from app.db.postgres import get_db
from app.db.models.user import User
from app.db.models.audit_log import AuditLog
from app.api.v1.dependencies import get_current_user
from app.guardrails.content_moderator import ContentModerator, ModerationStatus
from app.guardrails.pii_detector import PIIDetector
from app.guardrails.output_sanitizer import OutputSanitizer
from app.retrieval.metadata_filter import MetadataFilter
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.reranker import Reranker
from app.retrieval.clustering import CaseClustering
from app.retrieval.context_builder import ContextBuilder
from app.llm.prompt_builder import PromptBuilder
from app.llm.gpt_client import GPTClient
from app.llm.response_parser import ResponseParser
from app.scrapers.courtlistener_scraper import CourtListenerScraper
from app.utils.logger import logger

router = APIRouter(prefix="/chat", tags=["chat"])

# initialize all pipeline components once
moderator = ContentModerator()
pii_detector = PIIDetector()
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
    audit_log_id: str
    response_time_ms: int
    visa_type_detected: Optional[str]


@router.post("/query", response_model=QueryResponse)
async def query(
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start_time = time.time()
    logger.info(
        f"Query from user {current_user.email}: "
        f"'{body.query[:80]}...'"
    )

    # ── Step 1: Content moderation ─────────────────────────────────────
    mod_result = moderator.moderate(body.query)
    if not mod_result.is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=mod_result.reason,
        )

    # ── Step 2: PII detection on query ─────────────────────────────────
    pii_result = pii_detector.detect_and_redact(body.query)
    clean_query = pii_result.redacted_text

    if pii_result.pii_found:
        logger.warning(
            f"PII found in query from {current_user.email} — redacted"
        )

    # ── Step 3: Metadata filter ────────────────────────────────────────
    filter_context = await metadata_filter.build_filter_context(
        db=db,
        query=clean_query,
    )

    # ── Step 4: Hybrid retrieval + CourtListener simultaneously ────────
    law_chunks, case_chunks, court_cases = await _retrieve_all(
        db=db,
        query=clean_query,
        filter_context=filter_context,
        visa_type=filter_context.visa_type,
    )

    # ── Step 5: Rerank ─────────────────────────────────────────────────
    law_chunks = await reranker.rerank(
        query=clean_query,
        chunks=law_chunks,
    )
    case_chunks = await reranker.rerank(
        query=clean_query,
        chunks=case_chunks,
    )

    # ── Step 6: Cluster cases ──────────────────────────────────────────
    case_chunks = await clustering.cluster_and_select(
        chunks=case_chunks,
    )

    # ── Step 7: Build context ──────────────────────────────────────────
    context = await context_builder.build(
        db=db,
        law_chunks=law_chunks,
        case_chunks=case_chunks,
        court_cases=court_cases,
    )

    # ── Step 8: Build prompt ───────────────────────────────────────────
    prompt = prompt_builder.build(
        query=clean_query,
        context=context,
        visa_type=filter_context.visa_type,
    )

    # ── Step 9: GPT call ───────────────────────────────────────────────
    if body.stream:
        return StreamingResponse(
            _stream_response(prompt),
            media_type="text/event-stream",
        )

    gpt_response = await gpt_client.complete(prompt)

    # ── Step 10: Parse response ────────────────────────────────────────
    parsed = response_parser.parse(gpt_response)

    # ── Step 11: Sanitize output ───────────────────────────────────────
    sanitized = output_sanitizer.sanitize(
        raw_answer=parsed.answer,
        context=context,
    )

    # ── Step 12: Write audit log ───────────────────────────────────────
    end_time = time.time()
    response_time_ms = int((end_time - start_time) * 1000)

    audit_log = AuditLog(
        user_id=current_user.id,
        query=body.query,
        answer=sanitized.answer,
        retrieved_law_chunks=json.dumps(
            [c.chunk_id for c in law_chunks]
        ),
        retrieved_case_chunks=json.dumps(
            [c.chunk_id for c in case_chunks]
        ),
        visa_type_detected=filter_context.visa_type,
        response_time_ms=response_time_ms,
        token_count=gpt_response.total_tokens,
    )
    db.add(audit_log)
    await db.commit()
    await db.refresh(audit_log)

    logger.info(
        f"Query completed — {response_time_ms}ms, "
        f"{gpt_response.total_tokens} tokens, "
        f"{len(court_cases)} court cases found"
    )

    # format court cases for response
    court_cases_response = [
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

    return QueryResponse(
        answer=sanitized.answer,
        cited_laws=sanitized.law_citations,
        cited_cases=sanitized.case_citations,
        court_cases=court_cases_response,
        important_notes=parsed.important_notes,
        audit_log_id=str(audit_log.id),
        response_time_ms=response_time_ms,
        visa_type_detected=filter_context.visa_type,
    )


async def _retrieve_all(
    db,
    query: str,
    filter_context,
    visa_type: Optional[str],
) -> tuple:
    """
    Run Milvus retrieval and CourtListener search simultaneously
    using asyncio.gather for parallel execution.
    """
    scraper = CourtListenerScraper()

    try:
        milvus_task = hybrid_retriever.retrieve(
            db=db,
            query=query,
            filter_context=filter_context,
        )

        courtlistener_task = scraper.search(
            query=query,
            visa_type=visa_type,
            max_results=5,
        )

        # run both simultaneously
        results = await asyncio.gather(
            milvus_task,
            courtlistener_task,
            return_exceptions=True,
        )

        milvus_result = results[0]
        court_cases_result = results[1]

        # handle milvus result
        if isinstance(milvus_result, Exception):
            logger.error(f"Milvus retrieval failed: {milvus_result}")
            law_chunks = []
            case_chunks = []
        else:
            law_chunks, case_chunks = milvus_result

        # handle courtlistener result
        if isinstance(court_cases_result, Exception):
            logger.error(f"CourtListener search failed: {court_cases_result}")
            court_cases = []
        else:
            court_cases = court_cases_result

        logger.info(
            f"Parallel retrieval complete — "
            f"{len(law_chunks)} law chunks, "
            f"{len(case_chunks)} case chunks, "
            f"{len(court_cases)} court cases"
        )

        return law_chunks, case_chunks, court_cases

    finally:
        await scraper.close()


async def _stream_response(prompt):
    """Generator for streaming GPT response."""
    async for chunk in gpt_client.complete_streaming(prompt):
        yield f"data: {chunk}\n\n"
    yield "data: [DONE]\n\n"