import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class StudentInterest(Base):
    __tablename__ = "student_interests"
    __table_args__ = (
        UniqueConstraint("profile_id", name="uq_student_interests_profile_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution_name = Column(Text, nullable=False)
    degree_program = Column(Text, nullable=True)
    field_of_study = Column(Text, nullable=True)
    graduation_year = Column(Integer, nullable=True)
    skills = Column(Text, nullable=True)
    interest_areas = Column(Text, nullable=True)
    portfolio_url = Column(Text, nullable=True)
    github_url = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
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

    profile = relationship("Profile", back_populates="student_interest")


class IndustrialistInterest(Base):
    __tablename__ = "industrialist_interests"
    __table_args__ = (
        UniqueConstraint("profile_id", name="uq_industrialist_interests_profile_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_name = Column(Text, nullable=False)
    designation = Column(Text, nullable=True)
    industry_domain = Column(Text, nullable=True)
    focus_areas = Column(Text, nullable=True)
    company_website = Column(Text, nullable=True)
    sponsorship_capacity = Column(Text, nullable=True)
    collaboration_goals = Column(Text, nullable=True)
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

    profile = relationship("Profile", back_populates="industrialist_interest")
