import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import ApplicationStatus


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("issue_id", "student_id", name="uq_applications_issue_student"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_id = Column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proposal = Column(Text, nullable=False)
    status = Column(
        Text,
        nullable=False,
        default=ApplicationStatus.PENDING.value,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(  
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    issue = relationship("Issue", back_populates="applications")
    student = relationship("Profile", foreign_keys=[student_id], lazy="selectin")
