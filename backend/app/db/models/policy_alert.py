from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.db.postgres import Base


class PolicyAlert(Base):
    """USCIS policy/news change alerts from scraper."""
    __tablename__ = "policy_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False)
    source_type = Column(String(50), nullable=True)
    summary = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
