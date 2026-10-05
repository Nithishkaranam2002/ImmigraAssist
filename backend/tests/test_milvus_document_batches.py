"""Retrieval must search every law/case document, not only the first 50."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("MILVUS_HOST", "localhost")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app.retrieval.milvus_filter import (
    MILVUS_DOCUMENT_ID_BATCH,
    batched_document_ids,
    milvus_document_id_expr,
)


def test_batches_cover_every_document_id():
    """A full policy scrape is ~200 chapters. None of those IDs may be dropped."""
    document_ids = [f"doc-{i:04d}" for i in range(203)]
    batches = batched_document_ids(document_ids)

    assert [len(batch) for batch in batches] == [50, 50, 50, 50, 3]
    assert [doc_id for batch in batches for doc_id in batch] == document_ids
    assert all(len(batch) <= MILVUS_DOCUMENT_ID_BATCH for batch in batches)


def test_under_limit_stays_one_batch():
    document_ids = [f"doc-{i}" for i in range(50)]
    assert batched_document_ids(document_ids) == [document_ids]


def test_expr_lists_every_id_in_the_batch():
    expr = milvus_document_id_expr(["aaa", "bbb"])
    assert expr == 'document_id in ["aaa", "bbb"]'


def test_hybrid_search_queries_documents_past_the_first_batch(monkeypatch):
    """The retriever used to pass document_ids[:50] into one Milvus expression."""
    from app.retrieval.hybrid_retriever import HybridRetriever

    class _Hit:
        def __init__(self, document_id: str):
            self.score = 0.9
            self.entity = {
                "chunk_id": f"chunk-{document_id}",
                "document_id": document_id,
                "text": f"naturalization physical presence {document_id}",
                "section": "Vol 12",
                "clause": "",
                "doc_version": "1",
                "visa_type": "",
            }

    class _Collection:
        def __init__(self):
            self.exprs: list[str] = []

        def search(self, **kwargs):
            expr = kwargs["expr"]
            self.exprs.append(expr)
            # One hit from this batch so later batches are not short-circuited.
            first_id = expr.split('"')[1]
            return [[_Hit(first_id)]]

    monkeypatch.setattr(
        "app.retrieval.hybrid_retriever.OpenAIEmbeddings",
        lambda **kwargs: object(),
    )
    retriever = HybridRetriever()
    collection = _Collection()
    document_ids = [f"doc-{i:04d}" for i in range(120)]

    import asyncio

    results = asyncio.run(
        retriever._hybrid_search(
            query="naturalization physical presence requirements",
            query_embedding=[0.1, 0.2],
            collection=collection,
            document_ids=document_ids,
            source="law",
            top_k=8,
        )
    )

    assert len(collection.exprs) == 3
    assert "doc-0000" in collection.exprs[0]
    assert "doc-0050" in collection.exprs[1]
    assert "doc-0119" in collection.exprs[2]
    returned_ids = {chunk.document_id for chunk in results}
    # The fake collection returns the first ID of each batch, including the
    # batch that starts past the old 50-ID cutoff.
    assert returned_ids == {"doc-0000", "doc-0050", "doc-0100"}
