from sqlalchemy import Column, String, DateTime, Text, Integer, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum
from app.db.postgres import Base


class ScrapeStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    UNCHANGED = "unchanged"
    CHANGED = "changed"
    NEW = "new"


class ScrapeRecord(Base):
    __tablename__ = "scrape_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String(2000), nullable=False, unique=True, index=True)
    content_hash = Column(String(32), nullable=True)       # MD5 hash of content
    source_type = Column(String(50), nullable=True)        # uscis_policy, uscis_news, bia
    doc_type = Column(String(20), nullable=True)           # law or case
    title = Column(String(500), nullable=True)
    status = Column(SAEnum(ScrapeStatus), default=ScrapeStatus.NEW)
    error_message = Column(Text, nullable=True)
    last_scraped_at = Column(DateTime(timezone=True), nullable=True)
    last_changed_at = Column(DateTime(timezone=True), nullable=True)
    scrape_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<ScrapeRecord {self.url} ({self.status})>"
