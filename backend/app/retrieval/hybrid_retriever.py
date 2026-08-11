from dataclasses import dataclass
from typing import Optional
from rank_bm25 import BM25Okapi
from app.db.milvus import get_laws_collection, get_cases_collection
from app.retrieval.metadata_filter import FilterContext
from app.config import settings
from app.utils.logger import logger
from langsmith import traceable
from langchain_openai import OpenAIEmbeddings


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    text: str
    section: Optional[str]
    clause: Optional[str]
    doc_version: Optional[str]
    visa_type: Optional[str]
    source: str
    score: float
    vector_score: float
    bm25_score: float


class HybridRetriever:

    RRF_K = 60

    def __init__(self):
        self.embedder = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )

    async def retrieve(
        self,
        query: str,
        filter_context: FilterContext,
    ) -> tuple[list[RetrievedChunk], list[RetrievedChunk]]:

        logger.info(f"Hybrid retrieval for query (len={len(query)})")

        query_embedding = await self.embedder.aembed_query(query)

        law_chunks = await self._hybrid_search(
            query=query,
            query_embedding=query_embedding,
            collection=get_laws_collection(),
            document_ids=filter_context.law_document_ids,
            source="law",
            top_k=settings.TOP_K_LAWS,
        )
        case_chunks = await self._hybrid_search(
            query=query,
            query_embedding=query_embedding,
            collection=get_cases_collection(),
            document_ids=filter_context.case_document_ids,
            source="case",
            top_k=settings.TOP_K_CASES,
        )

        logger.info(
            f"Retrieved {len(law_chunks)} law chunks, "
            f"{len(case_chunks)} case chunks"
        )

        return law_chunks, case_chunks

    def _extract_field(self, hit, field_name: str) -> str:
        try:
            val = hit.entity.get(field_name)
            if val is not None:
                return str(val)
        except Exception:
            pass
        try:
            if hasattr(hit, 'fields'):
                return str(hit.fields.get(field_name, ""))
        except Exception:
            pass
        try:
            if hasattr(hit.entity, field_name):
                return str(getattr(hit.entity, field_name))
        except Exception:
            pass
        return ""

    async def _hybrid_search(
        self,
        query: str,
        query_embedding: list[float],
        collection,
        document_ids: list[str],
        source: str,
        top_k: int,
    ) -> list[RetrievedChunk]:

        if not document_ids:
            return []

        id_list = '", "'.join(document_ids[:50])
        expr = f'document_id in ["{id_list}"]'

        if source == "law":
            output_fields = [
                "chunk_id", "document_id", "text", "section",
                "clause", "doc_version", "visa_type",
            ]
        else:
            output_fields = [
                "chunk_id", "document_id", "text",
                "visa_type", "outcome", "jurisdiction",
            ]

        try:
            dense_results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param={
                    "metric_type": "COSINE",
                    "params": {"ef": settings.MILVUS_SEARCH_EF},
                },
                limit=top_k * 2,
                expr=expr,
                output_fields=output_fields,
            )
        except Exception as e:
            logger.error(f"Milvus search failed for {source}: {e}")
            return []

        dense_hits = []
        if dense_results and dense_results[0]:
            for hit in dense_results[0]:
                chunk_id = self._extract_field(hit, "chunk_id")
                document_id = self._extract_field(hit, "document_id")
                text = self._extract_field(hit, "text")
                doc_version = self._extract_field(hit, "doc_version")
                visa_type = self._extract_field(hit, "visa_type")

                if source == "law":
                    section = self._extract_field(hit, "section")
                    clause = self._extract_field(hit, "clause")
                else:
                    section = None
                    clause = None

                dense_hits.append({
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "text": text,
                    "section": section,
                    "clause": clause,
                    "doc_version": doc_version,
                    "visa_type": visa_type,
                    "vector_score": hit.score,
                })

        if not dense_hits:
            return []

        # BM25 sparse search
        texts = [h["text"] for h in dense_hits]
        tokenized = [t.lower().split() for t in texts]
        bm25 = BM25Okapi(tokenized)
        bm25_scores = bm25.get_scores(query.lower().split())

        max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1
        bm25_scores_norm = [s / max_bm25 for s in bm25_scores]

        for i, hit in enumerate(dense_hits):
            hit["bm25_score"] = bm25_scores_norm[i]

        # Reciprocal Rank Fusion
        dense_ranked = sorted(
            range(len(dense_hits)),
            key=lambda i: dense_hits[i]["vector_score"],
            reverse=True,
        )
        bm25_ranked = sorted(
            range(len(dense_hits)),
            key=lambda i: dense_hits[i]["bm25_score"],
            reverse=True,
        )

        rrf_scores = [0.0] * len(dense_hits)
        for rank, idx in enumerate(dense_ranked):
            rrf_scores[idx] += 1 / (self.RRF_K + rank + 1)
        for rank, idx in enumerate(bm25_ranked):
            rrf_scores[idx] += 1 / (self.RRF_K + rank + 1)

        final_ranked = sorted(
            range(len(dense_hits)),
            key=lambda i: rrf_scores[i],
            reverse=True,
        )[:top_k]

        results = []
        for idx in final_ranked:
            hit = dense_hits[idx]
            results.append(RetrievedChunk(
            chunk_id=hit["chunk_id"],
            document_id=hit["document_id"],
            text=hit["text"],
            section=hit["section"],
            clause=hit["clause"],
            doc_version=hit.get("doc_version", ""),
            visa_type=hit["visa_type"],
            source=source,
            score=rrf_scores[idx],
            vector_score=hit["vector_score"],
            bm25_score=hit["bm25_score"],
        ))
        return results