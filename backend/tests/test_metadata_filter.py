import asyncio

from app.db.models.document import DocumentType
from app.retrieval.metadata_filter import FilterContext, MetadataFilter


class StubMetadataFilter(MetadataFilter):
    async def _fetch_document_ids(
        self,
        db,
        doc_type: DocumentType,
        visa_type: str | None,
        year_min: int | None = None,
        year_max: int | None = None,
    ) -> list[str]:
        if doc_type == DocumentType.LAW and visa_type == "h4_ead":
            return ["law-h4-ead"]
        return []


def test_detect_visa_type_prefers_h4_ead_over_h4():
    assert (
        MetadataFilter()._detect_visa_type("What forms are needed for H-4 EAD?")
        == "h4_ead"
    )


def test_visa_override_does_not_reuse_all_case_docs_when_scoped_cases_missing():
    initial = FilterContext(
        visa_type=None,
        year_min=None,
        year_max=None,
        law_document_ids=["law-all"],
        case_document_ids=["case-all"],
    )

    scoped = asyncio.run(
        StubMetadataFilter().apply_visa_override(
            db=object(),
            filter_context=initial,
            visa_type="h4_ead",
        )
    )

    assert scoped.visa_type == "h4_ead"
    assert scoped.law_document_ids == ["law-h4-ead"]
    assert scoped.case_document_ids == []
