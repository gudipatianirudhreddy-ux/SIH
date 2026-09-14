import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import SolutionStatus


class Solution(Base):
    __tablename__ = "solutions"

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
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    pdf_url = Column(Text, nullable=True)
    prototype_url = Column(Text, nullable=True)
    status = Column(
        Text,
        nullable=False,
        default=SolutionStatus.SUBMITTED.value,
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

    issue = relationship("Issue", back_populates="solutions")
    student = relationship("Profile", foreign_keys=[student_id])
    reviews = relationship(
        "SolutionReview",
        back_populates="solution",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SolutionReview(Base):
    __tablename__ = "solution_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    solution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("solutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rating = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    solution = relationship("Solution", back_populates="reviews")
    reviewer = relationship("Profile", foreign_keys=[reviewer_id])
