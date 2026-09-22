import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PointTransaction(Base):
    __tablename__ = "point_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    points = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    issue_id = Column(UUID(as_uuid=True), ForeignKey("issues.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("Profile", foreign_keys=[user_id], lazy="selectin")
    issue = relationship("Issue", foreign_keys=[issue_id], lazy="selectin")
