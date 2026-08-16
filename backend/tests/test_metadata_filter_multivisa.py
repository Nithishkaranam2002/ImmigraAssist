"""Compare / dual-visa queries must retrieve every named corpus."""
import asyncio

from app.retrieval.metadata_filter import FilterContext, MetadataFilter


def test_compare_h1b_vs_l1_detects_both_visas():
    visas = MetadataFilter()._detect_visa_types(
        "Compare H1B vs L1 for intracompany transfer"
    )
    assert visas == ["h1b", "l1"]


def test_compare_h4_ead_vs_o1_keeps_specific_h4_ead():
    visas = MetadataFilter()._detect_visa_types(
        "Compare H-4 EAD vs O-1 for a dependent spouse"
    )
    assert "h4_ead" in visas
    assert "o1" in visas
    assert "h4" not in visas


def test_single_h1b_query_unchanged():
    mf = MetadataFilter()
    query = "What is the H-1B cap?"
    assert mf._detect_visa_types(query) == ["h1b"]
    assert mf._detect_visa_type(query) == "h1b"


def test_h4_ead_does_not_look_like_two_visas():
    """Bare H-4 also matches H-4 EAD; collapse so exclusive filters still apply."""
    visas = MetadataFilter()._detect_visa_types(
        "What are the requirements for H4 EAD eligibility?"
    )
    assert visas == ["h4_ead"]
    assert MetadataFilter()._detect_visa_type(
        "What are the requirements for H4 EAD eligibility?"
    ) == "h4_ead"


def test_asylum_only_query_is_single_visa():
    assert MetadataFilter()._detect_visa_types(
        "What documents are needed for an asylum application?"
    ) == ["asylum"]


def test_apply_visa_override_does_not_clobber_multi_visa_context():
    ctx = FilterContext(
        visa_type=None,
        year_min=None,
        year_max=None,
        law_document_ids=["h1b-doc", "l1-doc"],
        case_document_ids=["h1b-case"],
        visa_types=["h1b", "l1"],
    )

    async def _run():
        return await MetadataFilter().apply_visa_override(None, ctx, "asylum")

    result = asyncio.run(_run())
    assert result is ctx
    assert result.visa_types == ["h1b", "l1"]
    assert result.law_document_ids == ["h1b-doc", "l1-doc"]


def test_apply_visa_override_skips_when_query_already_named_a_visa():
    ctx = FilterContext(
        visa_type="h1b",
        year_min=None,
        year_max=None,
        law_document_ids=["h1b-doc"],
        case_document_ids=[],
        visa_types=["h1b"],
    )

    async def _run():
        return await MetadataFilter().apply_visa_override(None, ctx, "l1")

    result = asyncio.run(_run())
    assert result is ctx
    assert result.visa_type == "h1b"
