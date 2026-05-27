from sqlalchemy import Column, String, Integer, DateTime, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from app.db.postgres import Base


class DocumentType(str, enum.Enum):
    LAW = "law"
    CASE = "case"


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"         # uploaded, not yet ingested
    PROCESSING = "processing"   # ingestion in progress
    COMPLETED = "completed"     # ready to query
    FAILED = "failed"           # ingestion failed


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    doc_type = Column(SAEnum(DocumentType), nullable=False)
    status = Column(SAEnum(DocumentStatus), default=DocumentStatus.PENDING)
    version = Column(Integer, default=1)            # increments on re-upload
    visa_type = Column(String(100), nullable=True)  # h1b, h4, asylum etc
    effective_date = Column(DateTime(timezone=True), nullable=True)
    total_chunks = Column(Integer, default=0)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    error_message = Column(Text, nullable=True)     # if status=failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # relationships
    uploaded_by_user = relationship("User", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document")

    def __repr__(self):
        return f"<Document {self.filename} v{self.version} ({self.status})>"