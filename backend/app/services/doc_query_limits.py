"""Shared limits for /chat/doc-query document text."""

# Must stay in sync with DocQueryRequest.document_text max_length.
DOC_QUERY_MAX_CHARS = 50_000


def prepare_document_text(document_text: str) -> str:
    """
    Bound client document text for LLM context.

    Pydantic enforces DOC_QUERY_MAX_CHARS on the request body. This helper is
    defense-in-depth only — it must never clip below that schema limit, or
    trailing petition content is silently dropped from Doc Q&A.
    """
    if document_text is None:
        return ""
    return document_text[:DOC_QUERY_MAX_CHARS]
