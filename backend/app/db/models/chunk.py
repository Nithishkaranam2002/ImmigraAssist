from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.postgres import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    milvus_id = Column(String(100), nullable=True)      # ID returned by Milvus after insert
    chunk_index = Column(Integer, nullable=False)        # position in document
    text = Column(Text, nullable=False)                  # raw chunk text
    section = Column(String(200), nullable=True)         # Section 1
    clause = Column(String(200), nullable=True)          # Clause 1.3
    page_number = Column(Integer, nullable=True)
    visa_type = Column(String(100), nullable=True)
    doc_version = Column(String(50), nullable=True)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    document = relationship("Document", back_populates="chunks")
    section_maps = relationship("SectionMap", back_populates="chunk")

    def __repr__(self):
        return f"<Chunk {self.chunk_index} from doc {self.document_id}>"