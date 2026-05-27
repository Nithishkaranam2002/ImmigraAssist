from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.db.postgres import Base


class Case(Base):
    __tablename__ = "cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    case_number = Column(String(200), nullable=True, index=True)
    case_year = Column(Integer, nullable=True, index=True)
    visa_type = Column(String(100), nullable=True, index=True)
    outcome = Column(String(100), nullable=True)    # approved, denied, remanded
    jurisdiction = Column(String(200), nullable=True)
    judge = Column(String(200), nullable=True)
    summary = Column(Text, nullable=True)           # LLM generated summary
    cited_sections = Column(Text, nullable=True)    # JSON list of old section refs
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Case {self.case_number} ({self.visa_type}) {self.outcome}>"