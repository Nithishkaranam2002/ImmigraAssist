"""Build Milvus document_id filters without dropping part of the corpus."""

# Milvus boolean expressions stay reliable at this size. Callers must search
# every batch — using only the first batch silently omits the rest of the corpus.
MILVUS_DOCUMENT_ID_BATCH = 50


def batched_document_ids(
    document_ids: list[str],
    batch_size: int = MILVUS_DOCUMENT_ID_BATCH,
) -> list[list[str]]:
    """Split document IDs into filter batches, preserving every ID."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    return [
        document_ids[start : start + batch_size]
        for start in range(0, len(document_ids), batch_size)
    ]


def milvus_document_id_expr(document_ids: list[str]) -> str:
    """Milvus `in` expression for one batch of document IDs."""
    id_list = '", "'.join(document_ids)
    return f'document_id in ["{id_list}"]'
