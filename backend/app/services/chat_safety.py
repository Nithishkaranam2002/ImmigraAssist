from typing import Optional
from uuid import UUID


def should_cache_chat_response(
    *,
    matter_id: Optional[UUID],
    session_id: Optional[UUID],
) -> bool:
    """Chat responses include audit IDs and can include private context; do not share them."""
    return False
