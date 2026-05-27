from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.postgres import Base


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    audit_log_id = Column(UUID(as_uuid=True), ForeignKey("audit_logs.id"), nullable=False)
    is_positive = Column(Boolean, nullable=False)       # True = thumbs up
    comment = Column(Text, nullable=True)               # optional written feedback
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    user = relationship("User", back_populates="feedbacks")
    audit_log = relationship("AuditLog", back_populates="feedback")

    def __repr__(self):
        return f"<Feedback {'👍' if self.is_positive else '👎'} by user={self.user_id}>"