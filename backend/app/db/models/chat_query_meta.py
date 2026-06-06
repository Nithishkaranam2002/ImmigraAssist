from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.db.postgres import Base


class ChatQueryMeta(Base):
    """Extended metadata for chat queries (confidence, structured fields)."""
    __tablename__ = "chat_query_meta"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_log_id = Column(UUID(as_uuid=True), ForeignKey("audit_logs.id"), unique=True, nullable=False)
    matter_id = Column(UUID(as_uuid=True), ForeignKey("matters.id"), nullable=True)
    session_id = Column(UUID(as_uuid=True), nullable=True)
    confidence_score = Column(Float, nullable=True)
    confidence_level = Column(String(20), nullable=True)
    next_steps = Column(Text, nullable=True)
    risks = Column(Text, nullable=True)
    related_forms = Column(Text, nullable=True)
    query_mode = Column(String(30), default="standard")
    from_cache = Column(Boolean, default=False)
    needs_review = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
