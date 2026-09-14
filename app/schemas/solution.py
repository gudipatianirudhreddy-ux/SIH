from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SolutionStatus


class SolutionReviewCreate(BaseModel):
    rating: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Rating from 1 to 5",
    )
    feedback: str = Field(..., min_length=1, description="Constructive feedback or evaluation")


class SolutionReviewResponse(BaseModel):
    id: uuid.UUID
    solution_id: uuid.UUID
    reviewer_id: uuid.UUID
    rating: Optional[int] = None
    feedback: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SolutionBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, description="Solution / proposal title")
    description: str = Field(..., min_length=5, description="Comprehensive proposal or methodology description")
    pdf_url: Optional[str] = Field(default=None, description="URL to solution report/documentation PDF")
    prototype_url: Optional[str] = Field(default=None, description="URL to live demo, repository, or prototype")


class SolutionCreate(SolutionBase):
    pass


class SolutionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, min_length=5)
    pdf_url: Optional[str] = None
    prototype_url: Optional[str] = None
    status: Optional[SolutionStatus] = None


class SolutionResponse(SolutionBase):
    id: uuid.UUID
    issue_id: uuid.UUID
    student_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime
    reviews: List[SolutionReviewResponse] = []

    model_config = ConfigDict(from_attributes=True)
