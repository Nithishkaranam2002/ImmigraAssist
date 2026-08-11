from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.db.models.user import User
from app.api.v1.dependencies import get_current_user
from app.scrapers.courtlistener_scraper import CourtListenerScraper
from app.utils.logger import logger

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("/search")
async def search_cases(
    q: str = Query(..., description="Search query"),
    visa_type: Optional[str] = Query(None, description="Visa type filter"),
    max_results: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
):
    """
    Search CourtListener for relevant immigration cases.
    Returns real case citations with links.
    """
    logger.info(f"Case search by {current_user.email} (len={len(q)})")

    scraper = CourtListenerScraper()
    try:
        cases = await scraper.search(
            query=q,
            visa_type=visa_type,
            max_results=max_results,
        )

        return {
            "query": q,
            "visa_type": visa_type,
            "total": len(cases),
            "cases": [
                {
                    "case_name": c.case_name,
                    "case_id": c.case_id,
                    "court": c.court_name,
                    "date_decided": c.date_decided,
                    "citation": c.citation,
                    "summary": c.summary,
                    "courtlistener_url": c.courtlistener_url,
                    "visa_types": c.visa_types,
                    "outcome": c.outcome,
                    "relevance_score": c.relevance_score,
                }
                for c in cases
            ],
        }
    finally:
        await scraper.close()