from dataclasses import dataclass
import cohere
from app.retrieval.hybrid_retriever import RetrievedChunk
from app.config import settings
from app.utils.logger import logger
import os


class Reranker:
    """
    Cross-encoder reranker using Cohere Rerank API.
    Takes top-k hybrid results and reorders by true relevance.

    Why cross-encoder beats bi-encoder for reranking:
    Bi-encoder (embeddings) encodes query and doc separately.
    Cross-encoder sees query + doc together → much more accurate.
    We only run it on top-k (not all chunks) to keep it fast.
    """

    def __init__(self):
        self.client = cohere.Client(
            api_key=os.getenv("COHERE_API_KEY", "")
        )

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_n: int | None = None,
    ) -> list[RetrievedChunk]:
        """
        Rerank chunks by relevance to query.
        Returns top_n most relevant chunks in new order.
        """
        if not chunks:
            return []

        top_n = top_n or settings.RERANKER_TOP_N

        # if too few chunks just return as is
        if len(chunks) <= 2:
            return chunks[:top_n]

        logger.info(f"Reranking {len(chunks)} chunks → top {top_n}")

        try:
            documents = [c.text[:2000] for c in chunks]  # cohere has input limit

            response = self.client.rerank(
                model="rerank-english-v3.0",
                query=query,
                documents=documents,
                top_n=top_n,
            )

            reranked = []
            for result in response.results:
                chunk = chunks[result.index]
                # update score with reranker score
                chunk.score = result.relevance_score
                reranked.append(chunk)

            logger.info(f"Reranking complete — top score: {reranked[0].score:.3f}")
            return reranked

        except Exception as e:
            logger.error(f"Reranker failed: {e} — falling back to original order")
            return chunks[:top_n]