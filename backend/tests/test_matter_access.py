import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import HTTPException

from app.services.matter_access import detach_matter_research, require_owned_matter


def _db_returning(value):
    result = MagicMock()
    result.scalars.return_value.first.return_value = value
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    return db


def test_require_owned_matter_returns_matching_matter():
    matter = object()
    db = _db_returning(matter)

    returned = asyncio.run(require_owned_matter(db, uuid4(), uuid4()))

    assert returned is matter
    statement = db.execute.await_args.args[0]
    sql = str(statement)
    assert "matters.id" in sql
    assert "matters.user_id" in sql


def test_require_owned_matter_hides_missing_or_foreign_matter():
    db = _db_returning(None)

    try:
        asyncio.run(require_owned_matter(db, uuid4(), uuid4()))
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "Matter not found"
    else:
        raise AssertionError("Foreign or missing matter should be rejected")


def test_detach_matter_research_clears_every_reference():
    db = MagicMock()
    db.execute = AsyncMock()
    matter_id = uuid4()

    asyncio.run(detach_matter_research(db, matter_id))

    statement = db.execute.await_args.args[0]
    compiled = statement.compile()
    sql = str(compiled)
    assert sql.startswith("UPDATE chat_query_meta SET matter_id=")
    assert "WHERE chat_query_meta.matter_id =" in sql
    assert "audit_log_id" not in sql
    assert matter_id in compiled.params.values()
    assert None in compiled.params.values()
