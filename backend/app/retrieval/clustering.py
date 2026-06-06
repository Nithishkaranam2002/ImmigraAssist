from app.retrieval.hybrid_retriever import RetrievedChunk
from app.utils.logger import logger


class CaseClustering:
    """
    Deduplicate case chunks by document_id without extra embedding calls.
    Picks the highest-scoring chunk per document — fast and avoids
    sending multiple chunks from the same case to GPT.
    """

    async def cluster_and_select(
        self,
        chunks: list[RetrievedChunk],
        max_clusters: int = 5,
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []

        if len(chunks) <= max_clusters:
            return chunks

        logger.info(f"Deduplicating {len(chunks)} case chunks by document")

        best_by_doc: dict[str, RetrievedChunk] = {}
        for chunk in chunks:
            doc_key = chunk.document_id or chunk.chunk_id
            existing = best_by_doc.get(doc_key)
            if not existing or chunk.score > existing.score:
                best_by_doc[doc_key] = chunk

        representatives = sorted(
            best_by_doc.values(),
            key=lambda c: c.score,
            reverse=True,
        )[:max_clusters]

        logger.info(f"Selected {len(representatives)} unique case chunks")
        return representatives
