import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(String(50), nullable=False)
    title = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    related_issue_id = Column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    related_application_id = Column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    related_collaboration_id = Column(
        UUID(as_uuid=True),
        ForeignKey("collaborations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_read = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    recipient = relationship("Profile", foreign_keys=[recipient_id])
    issue = relationship("Issue", foreign_keys=[related_issue_id])
    application = relationship("Application", foreign_keys=[related_application_id])
    collaboration = relationship("Collaboration", foreign_keys=[related_collaboration_id])
