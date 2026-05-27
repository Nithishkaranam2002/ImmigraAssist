from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.postgres import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    query = Column(Text, nullable=False)                # what the user asked
    answer = Column(Text, nullable=True)                # what GPT returned
    retrieved_law_chunks = Column(Text, nullable=True)  # JSON list of chunk IDs
    retrieved_case_chunks = Column(Text, nullable=True) # JSON list of chunk IDs
    visa_type_detected = Column(String(100), nullable=True)
    response_time_ms = Column(Integer, nullable=True)   # how fast was the response
    token_count = Column(Integer, nullable=True)        # GPT tokens used
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    user = relationship("User", back_populates="audit_logs")
    feedback = relationship("Feedback", back_populates="audit_log", uselist=False)

    def __repr__(self):
        return f"<AuditLog user={self.user_id} at={self.created_at}>"