from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.postgres import Base


class Matter(Base):
    """Client/case workspace for tagging research queries."""
    __tablename__ = "matters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(300), nullable=False)
    client_name = Column(String(200), nullable=True)
    visa_type = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(30), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="matters")
