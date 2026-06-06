import asyncio
import cohere
from app.retrieval.hybrid_retriever import RetrievedChunk
from app.config import settings
from app.utils.logger import logger
import os


class Reranker:
    """
    Cross-encoder reranker using Cohere Rerank API.
    Runs in a thread pool to avoid blocking the async event loop.
    """

    def __init__(self):
        api_key = os.getenv("COHERE_API_KEY", "")
        self.client = cohere.Client(api_key=api_key) if api_key else None

    def _rerank_sync(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_n: int,
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []

        if len(chunks) <= 2:
            return chunks[:top_n]

        if not self.client:
            return chunks[:top_n]

        documents = [c.text[:2000] for c in chunks]
        response = self.client.rerank(
            model="rerank-english-v3.0",
            query=query,
            documents=documents,
            top_n=top_n,
        )

        reranked = []
        for result in response.results:
            chunk = chunks[result.index]
            chunk.score = result.relevance_score
            reranked.append(chunk)
        return reranked

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_n: int | None = None,
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []

        top_n = top_n or settings.RERANKER_TOP_N

        if len(chunks) <= 2:
            return chunks[:top_n]

        logger.info(f"Reranking {len(chunks)} chunks → top {top_n}")

        try:
            reranked = await asyncio.to_thread(
                self._rerank_sync, query, chunks, top_n
            )
            if reranked:
                logger.info(f"Reranking complete — top score: {reranked[0].score:.3f}")
            return reranked
        except Exception as e:
            logger.error(f"Reranker failed: {e} — falling back to original order")
            return chunks[:top_n]
