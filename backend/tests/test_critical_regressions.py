import asyncio
import enum
import os
import sys
import types
import unittest


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)


class _Logger:
    def debug(self, *_args, **_kwargs):
        pass

    def info(self, *_args, **_kwargs):
        pass

    def warning(self, *_args, **_kwargs):
        pass

    def error(self, *_args, **_kwargs):
        pass


class ScrapeStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    UNCHANGED = "unchanged"
    CHANGED = "changed"
    NEW = "new"


def _install_dependency_stubs():
    logger_module = types.ModuleType("app.utils.logger")
    logger_module.logger = _Logger()
    sys.modules["app.utils.logger"] = logger_module

    config_module = types.ModuleType("app.config")
    config_module.settings = types.SimpleNamespace(
        EMBEDDING_MODEL="test-embedding-model",
        OPENAI_API_KEY="test-key",
        MILVUS_SEARCH_EF=64,
    )
    sys.modules["app.config"] = config_module

    milvus_module = types.ModuleType("app.db.milvus")
    milvus_module.get_laws_collection = lambda: None
    milvus_module.get_cases_collection = lambda: None
    sys.modules["app.db.milvus"] = milvus_module

    metadata_filter_module = types.ModuleType("app.retrieval.metadata_filter")
    metadata_filter_module.FilterContext = object
    sys.modules["app.retrieval.metadata_filter"] = metadata_filter_module

    langchain_openai_module = types.ModuleType("langchain_openai")
    langchain_openai_module.OpenAIEmbeddings = object
    sys.modules["langchain_openai"] = langchain_openai_module

    rank_bm25_module = types.ModuleType("rank_bm25")

    class BM25Okapi:
        def __init__(self, tokenized_corpus):
            self.tokenized_corpus = tokenized_corpus

        def get_scores(self, query_terms):
            return [
                sum(tokens.count(term) for term in query_terms)
                for tokens in self.tokenized_corpus
            ]

    rank_bm25_module.BM25Okapi = BM25Okapi
    sys.modules["rank_bm25"] = rank_bm25_module

    celery_module = types.ModuleType("celery")
    celery_module.Task = object
    sys.modules["celery"] = celery_module

    celery_app_module = types.ModuleType("app.tasks.celery_app")

    class CeleryAppStub:
        def task(self, *_args, **_kwargs):
            def decorator(func):
                return func

            return decorator

    celery_app_module.celery_app = CeleryAppStub()
    sys.modules["app.tasks.celery_app"] = celery_app_module

    postgres_module = types.ModuleType("app.db.postgres")
    postgres_module.AsyncSessionLocal = object
    sys.modules["app.db.postgres"] = postgres_module

    sqlalchemy_module = types.ModuleType("sqlalchemy")
    sqlalchemy_module.select = lambda *_args, **_kwargs: None
    sys.modules["sqlalchemy"] = sqlalchemy_module

    sqlalchemy_ext_module = types.ModuleType("sqlalchemy.ext")
    sys.modules["sqlalchemy.ext"] = sqlalchemy_ext_module

    sqlalchemy_asyncio_module = types.ModuleType("sqlalchemy.ext.asyncio")
    sqlalchemy_asyncio_module.AsyncSession = object
    sys.modules["sqlalchemy.ext.asyncio"] = sqlalchemy_asyncio_module

    scrape_record_module = types.ModuleType("app.db.models.scrape_record")
    scrape_record_module.ScrapeStatus = ScrapeStatus
    scrape_record_module.ScrapeRecord = object
    sys.modules["app.db.models.scrape_record"] = scrape_record_module

    orchestrator_module = types.ModuleType("app.scrapers.scraper_orchestrator")
    orchestrator_module.ScraperOrchestrator = object
    sys.modules["app.scrapers.scraper_orchestrator"] = orchestrator_module


_install_dependency_stubs()


class _FakeEntity:
    def __init__(self, fields):
        self._fields = fields

    def get(self, field_name):
        return self._fields.get(field_name)


class _FakeHit:
    def __init__(self, fields, score):
        self.entity = _FakeEntity(fields)
        self.score = score


class _FakeCollection:
    def __init__(self):
        self.search_exprs = []

    def search(self, *, expr, **_kwargs):
        self.search_exprs.append(expr)
        if len(self.search_exprs) == 1:
            document_id = "doc-000"
            text = "general immigration text"
            score = 0.4
        else:
            document_id = "doc-074"
            text = "needle appears in a later policy chapter"
            score = 0.9

        return [[
            _FakeHit(
                {
                    "chunk_id": f"chunk-{document_id}",
                    "document_id": document_id,
                    "text": text,
                    "section": "",
                    "clause": "",
                    "doc_version": "1",
                    "visa_type": "",
                },
                score,
            )
        ]]


class CriticalRegressionTests(unittest.TestCase):
    def test_hybrid_search_queries_all_document_id_chunks(self):
        from app.retrieval.hybrid_retriever import HybridRetriever

        retriever = HybridRetriever.__new__(HybridRetriever)
        collection = _FakeCollection()
        document_ids = [f"doc-{index:03d}" for index in range(75)]

        results = asyncio.run(
            retriever._hybrid_search(
                query="needle",
                query_embedding=[0.0],
                collection=collection,
                document_ids=document_ids,
                source="law",
                top_k=5,
            )
        )

        self.assertEqual(2, len(collection.search_exprs))
        self.assertEqual(50, collection.search_exprs[0].count("doc-"))
        self.assertEqual(25, collection.search_exprs[1].count("doc-"))
        self.assertIn("doc-074", {chunk.document_id for chunk in results})

    def test_missing_policy_selector_retries_failed_urls(self):
        from app.tasks.scraper_task import _select_policy_urls_to_scrape

        urls_to_scrape = _select_policy_urls_to_scrape(
            all_urls={"missing", "failed", "success"},
            recorded_urls=[
                ("failed", ScrapeStatus.FAILED),
                ("success", ScrapeStatus.SUCCESS),
            ],
        )

        self.assertEqual(["failed", "missing"], urls_to_scrape)

    def test_failed_scrape_preserves_last_good_hash(self):
        from app.scrapers.change_detector import ChangeDetector

        detector = ChangeDetector()

        self.assertEqual(
            "previous-good-hash",
            detector._hash_for_update(
                old_hash="previous-good-hash",
                new_hash="",
                status=ScrapeStatus.FAILED,
            ),
        )
        self.assertEqual(
            "new-good-hash",
            detector._hash_for_update(
                old_hash="previous-good-hash",
                new_hash="new-good-hash",
                status=ScrapeStatus.CHANGED,
            ),
        )


if __name__ == "__main__":
    unittest.main()
