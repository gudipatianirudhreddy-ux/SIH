import uuid
from sqlalchemy import Column, DateTime, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import IssueStatus


class Issue(Base):
    __tablename__ = "issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(Text, nullable=True, index=True)
    category_confidence = Column(Float, nullable=True)
    status = Column(
        Text,
        nullable=False,
        default=IssueStatus.REPORTED.value,
        index=True,
    )
    priority = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(Text, nullable=True)
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

    reporter = relationship("Profile", foreign_keys=[reporter_id])
    media = relationship(
        "IssueMedia",
        back_populates="issue",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    solutions = relationship(
        "Solution",
        back_populates="issue",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class IssueMedia(Base):
    __tablename__ = "issue_media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_id = Column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    media_url = Column(Text, nullable=False)
    media_type = Column(Text, nullable=False, default="image")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    issue = relationship("Issue", back_populates="media")
