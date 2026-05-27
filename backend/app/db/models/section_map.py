from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.postgres import Base


class SectionMap(Base):
    __tablename__ = "section_maps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # old reference found inside a case file
    old_section_ref = Column(String(200), nullable=False)   # e.g. "Section 1, Clause 1.3"
    old_doc_year = Column(String(10), nullable=True)        # e.g. "2020"

    # what it maps to in the current policy doc
    current_chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id"), nullable=False)
    current_section = Column(String(200), nullable=True)    # e.g. "Section 3, Clause 2.1"
    current_doc_version = Column(String(50), nullable=True) # e.g. "2026"

    # confidence of the semantic match
    similarity_score = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    chunk = relationship("Chunk", back_populates="section_maps")

    def __repr__(self):
        return f"<SectionMap '{self.old_section_ref}' → '{self.current_section}' score={self.similarity_score}>"