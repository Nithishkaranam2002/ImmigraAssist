import uuid

from app.services.chat_safety import should_cache_chat_response


def test_chat_responses_are_not_cached_without_context():
    assert not should_cache_chat_response(matter_id=None, session_id=None)


def test_chat_responses_are_not_cached_with_private_context():
    assert not should_cache_chat_response(
        matter_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
    )
