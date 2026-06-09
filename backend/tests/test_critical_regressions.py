import asyncio
import importlib
import pkgutil
import sys
import types
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.sql.dml import Update


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


class _Result:
    def __init__(self, scalars=None, rows=None):
        self._scalars = scalars or []
        self._rows = rows or []

    def scalars(self):
        return _ScalarResult(self._scalars)

    def fetchall(self):
        return self._rows


class _SequenceDb:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.statements = []
        self.added = []
        self.deleted = []
        self.committed = False

    async def execute(self, stmt):
        self.statements.append(stmt)
        return self.results.pop(0) if self.results else _Result()

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        for obj in self.added:
            if hasattr(obj, "id") and getattr(obj, "id") is None:
                obj.id = uuid.uuid4()

    async def refresh(self, _obj):
        return None

    async def delete(self, obj):
        self.deleted.append(obj)

    async def commit(self):
        self.committed = True


def _user(user_id=None):
    uid = user_id or uuid.uuid4()
    return types.SimpleNamespace(
        id=uid,
        email=f"{uid}@example.com",
    )


def _import_all_models():
    import app.db.models

    for module_info in pkgutil.iter_modules(app.db.models.__path__):
        importlib.import_module(f"app.db.models.{module_info.name}")


def _install_chat_import_stubs():
    class _Dummy:
        def __init__(self, *args, **kwargs):
            pass

    def module(name, **attrs):
        mod = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(mod, key, value)
        sys.modules[name] = mod

    module("app.guardrails.content_moderator", ContentModerator=_Dummy)
    module("app.guardrails.pii_detector", get_pii_detector=lambda: _Dummy())
    module("app.guardrails.output_sanitizer", OutputSanitizer=_Dummy)
    module("app.retrieval.metadata_filter", MetadataFilter=_Dummy)
    module("app.retrieval.hybrid_retriever", HybridRetriever=_Dummy)
    module("app.retrieval.reranker", Reranker=_Dummy)
    module("app.retrieval.clustering", CaseClustering=_Dummy)
    module("app.retrieval.context_builder", ContextBuilder=_Dummy)
    module("app.llm.prompt_builder", PromptBuilder=_Dummy)
    module("app.llm.gpt_client", GPTClient=_Dummy, GPTResponse=_Dummy)
    module("app.llm.response_parser", ParsedResponse=_Dummy, ResponseParser=_Dummy)
    module("app.scrapers.courtlistener_scraper", CourtListenerScraper=_Dummy)
    module("app.services.answer_quality", assess_and_enhance=lambda **_kwargs: None)


def test_query_cache_key_is_scoped_by_user():
    from app.services.query_cache import _cache_key

    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    assert _cache_key(" H4 EAD? ", "standard", user_a) == _cache_key(
        "h4 ead?", "standard", user_a
    )
    assert _cache_key("H4 EAD?", "standard", user_a) != _cache_key(
        "H4 EAD?", "standard", user_b
    )


def test_cached_chat_response_gets_fresh_audit_and_meta():
    _import_all_models()
    _install_chat_import_stubs()
    sys.modules.pop("app.api.v1.routes.chat", None)
    chat = importlib.import_module("app.api.v1.routes.chat")
    from app.db.models.audit_log import AuditLog
    from app.db.models.chat_query_meta import ChatQueryMeta

    db = _SequenceDb()
    user = _user()
    stale_audit_id = str(uuid.uuid4())
    session_id = uuid.uuid4()
    matter_id = uuid.uuid4()

    response = asyncio.run(
        chat._record_cached_response(
            db=db,
            current_user=user,
            raw_query="What are H4 EAD requirements?",
            cached={
                "answer": "Cached answer",
                "cited_laws": [],
                "cited_cases": [],
                "court_cases": [],
                "important_notes": [],
                "next_steps": ["File I-765"],
                "risks": [],
                "related_forms": ["I-765"],
                "audit_log_id": stale_audit_id,
                "response_time_ms": 999,
                "visa_type_detected": "h4",
                "confidence_score": 0.8,
                "confidence_level": "high",
                "confidence_label": "High confidence",
            },
            matter_id=matter_id,
            session_id=session_id,
            query_mode="standard",
            start_time=0,
        )
    )

    audit_log = next(obj for obj in db.added if isinstance(obj, AuditLog))
    meta = next(obj for obj in db.added if isinstance(obj, ChatQueryMeta))
    assert response["audit_log_id"] == str(audit_log.id)
    assert response["audit_log_id"] != stale_audit_id
    assert response["from_cache"] is True
    assert response["session_id"] == str(session_id)
    assert response["matter_id"] == str(matter_id)
    assert audit_log.user_id == user.id
    assert meta.audit_log_id == audit_log.id
    assert meta.session_id == session_id
    assert meta.matter_id == matter_id
    assert meta.from_cache is True


def test_feedback_lookup_requires_current_user_ownership():
    from app.api.v1.routes import feedback

    db = _SequenceDb([_Result()])
    user = _user()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            feedback.submit_feedback(
                feedback.FeedbackRequest(
                    audit_log_id=str(uuid.uuid4()),
                    is_positive=True,
                ),
                db=db,
                current_user=user,
            )
        )

    assert exc.value.status_code == 404
    statement = str(db.statements[0])
    assert "audit_logs.user_id" in statement


def test_attach_research_falls_back_to_owned_session_rows_when_ids_are_stale():
    _import_all_models()
    from app.api.v1.routes import matters
    from app.db.models.audit_log import AuditLog
    from app.db.models.chat_query_meta import ChatQueryMeta
    from app.db.models.matter import Matter

    user = _user()
    stale_id = uuid.uuid4()
    owned_id = uuid.uuid4()
    session_id = uuid.uuid4()
    audit_log = AuditLog(id=owned_id, user_id=user.id, query="Q", answer="A")
    meta = ChatQueryMeta(audit_log_id=owned_id, session_id=session_id)
    db = _SequenceDb(
        [
            _Result(rows=[(owned_id,)]),
            _Result(),
            _Result(scalars=[audit_log]),
            _Result(scalars=[meta]),
        ]
    )

    response = asyncio.run(
        matters.attach_research(
            matters.AttachResearchRequest(
                title="New matter",
                audit_log_ids=[stale_id],
                session_id=session_id,
            ),
            db=db,
            current_user=user,
        )
    )

    matter = next(obj for obj in db.added if isinstance(obj, Matter))
    assert response["attached_count"] == 1
    assert response["matter_id"] == str(matter.id)
    assert meta.matter_id == matter.id
    assert db.committed is True


def test_attach_research_rejects_zero_owned_attachments():
    _import_all_models()
    from app.api.v1.routes import matters

    db = _SequenceDb([_Result()])

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            matters.attach_research(
                matters.AttachResearchRequest(
                    title="Empty matter",
                    audit_log_ids=[uuid.uuid4()],
                ),
                db=db,
                current_user=_user(),
            )
        )

    assert exc.value.status_code == 400
    assert db.committed is False


def test_delete_matter_unlinks_chat_meta_before_delete():
    _import_all_models()
    from app.api.v1.routes import matters
    from app.db.models.matter import Matter

    user = _user()
    matter = Matter(id=uuid.uuid4(), user_id=user.id, title="Client")
    db = _SequenceDb([_Result(scalars=[matter]), _Result()])

    response = asyncio.run(
        matters.delete_matter(matter_id=matter.id, db=db, current_user=user)
    )

    update_stmt = next(stmt for stmt in db.statements if isinstance(stmt, Update))
    assert "chat_query_meta" in str(update_stmt)
    assert response == {"message": "Deleted"}
    assert db.deleted == [matter]
    assert db.committed is True
