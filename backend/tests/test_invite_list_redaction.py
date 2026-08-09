"""Invite list responses must never re-expose plaintext tokens."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.api.v1.routes.invites import _invite_list_item, list_invites
from app.db.models.user import UserRole


def test_invite_list_item_omits_token_and_link_fields():
    secret = "super-secret-invite-token-value"
    invite = SimpleNamespace(
        id=uuid4(),
        token=secret,
        email="partner@example.com",
        role=UserRole.SUPER_ADMIN,
        designation="Managing Partner",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_used=False,
    )

    item = _invite_list_item(invite)
    payload = item.model_dump()

    assert "token" not in payload
    assert "invite_link" not in payload
    assert secret not in str(payload)
    assert payload["email"] == "partner@example.com"
    assert payload["role"] == UserRole.SUPER_ADMIN.value
    assert payload["is_used"] is False


@pytest.mark.asyncio
async def test_list_invites_does_not_return_plaintext_tokens():
    secret = "unused-privileged-invite-token"
    invite = SimpleNamespace(
        id=uuid4(),
        token=secret,
        email=None,
        role=UserRole.ADMIN,
        designation=None,
        expires_at=datetime.now(timezone.utc) + timedelta(days=3),
        is_used=False,
        created_at=datetime.now(timezone.utc),
    )

    result = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [invite]),
    )
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)
    current_user = SimpleNamespace(id=uuid4(), role=UserRole.ADMIN)

    items = await list_invites(db=db, current_user=current_user)

    assert len(items) == 1
    payload = items[0].model_dump()
    assert "token" not in payload
    assert "invite_link" not in payload
    assert secret not in str(payload)
    assert payload["role"] == UserRole.ADMIN.value
