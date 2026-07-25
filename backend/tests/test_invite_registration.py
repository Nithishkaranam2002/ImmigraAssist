"""Invite registration must row-lock so general invites cannot be reused concurrently."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.v1.routes.auth import _load_invite_for_registration
from app.db.models.invite import Invite
from app.db.models.user import UserRole


def test_invite_registration_query_uses_for_update():
    """The invite lookup used at registration must request a row lock."""
    stmt = select(Invite).where(Invite.token == "tok").with_for_update()
    assert stmt._for_update_arg is not None


@pytest.mark.asyncio
async def test_load_invite_locks_row_before_validation():
    now = datetime.now(timezone.utc)
    invite = SimpleNamespace(
        token="shared-token",
        email=None,
        role=UserRole.ADMIN,
        designation="Partner",
        is_used=False,
        expires_at=now + timedelta(days=1),
    )

    result = SimpleNamespace(
        scalars=lambda: SimpleNamespace(first=lambda: invite),
    )
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)

    loaded = await _load_invite_for_registration(db, "shared-token", "a@example.com")
    assert loaded is invite

    stmt = db.execute.await_args.args[0]
    assert stmt._for_update_arg is not None


@pytest.mark.asyncio
async def test_load_invite_rejects_already_used():
    invite = SimpleNamespace(
        token="used-token",
        email=None,
        role=UserRole.ATTORNEY,
        designation=None,
        is_used=True,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    result = SimpleNamespace(
        scalars=lambda: SimpleNamespace(first=lambda: invite),
    )
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)

    with pytest.raises(HTTPException) as exc:
        await _load_invite_for_registration(db, "used-token", "b@example.com")
    assert exc.value.status_code == 400
    assert "already used" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_load_invite_rejects_email_mismatch():
    invite = SimpleNamespace(
        token="bound-token",
        email="intended@example.com",
        role=UserRole.ATTORNEY,
        designation=None,
        is_used=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    result = SimpleNamespace(
        scalars=lambda: SimpleNamespace(first=lambda: invite),
    )
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)

    with pytest.raises(HTTPException) as exc:
        await _load_invite_for_registration(db, "bound-token", "other@example.com")
    assert exc.value.status_code == 400
    assert "different email" in exc.value.detail.lower()
