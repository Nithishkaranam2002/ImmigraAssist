"""Regression: Doc Q&A must not silently drop text below the API max_length."""

from pathlib import Path

from app.services.doc_query_limits import DOC_QUERY_MAX_CHARS, prepare_document_text

CHAT_ROUTE = (
    Path(__file__).resolve().parents[1] / "app" / "api" / "v1" / "routes" / "chat.py"
)


def test_prepare_document_text_preserves_full_schema_budget():
    """A petition of schema max length must reach the model intact."""
    document = "A" * DOC_QUERY_MAX_CHARS
    assert len(prepare_document_text(document)) == DOC_QUERY_MAX_CHARS
    assert prepare_document_text(document) == document


def test_prepare_document_text_keeps_content_past_former_30k_clip():
    """
    Trigger: attorney pastes ~40k petition (allowed by max_length=50000) and
    asks about language near the end. The old [:30000] slice dropped that text
    with no error, so Doc Q&A answered without seeing the cited section.
    """
    marker = "UNIQUE_TRAILING_CLAUSE_FOR_REVIEW"
    document = ("B" * 35000) + marker
    assert len(document) < DOC_QUERY_MAX_CHARS
    prepared = prepare_document_text(document)
    assert marker in prepared
    assert prepared.endswith(marker)


def test_doc_query_route_uses_shared_limit_without_silent_30k_clip():
    """Route schema and prepare helper must share DOC_QUERY_MAX_CHARS."""
    text = CHAT_ROUTE.read_text()
    assert "from app.services.doc_query_limits import DOC_QUERY_MAX_CHARS, prepare_document_text" in text
    assert "max_length=DOC_QUERY_MAX_CHARS" in text
    assert "prepare_document_text(body.document_text)" in text
    assert "document_text[:30000]" not in text
