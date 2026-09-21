from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApplicationStatus
from app.schemas.profile import ProfileResponse


class ApplicationBase(BaseModel):
    proposal: str = Field(
        ...,
        min_length=5,
        description="Detailed proposal, methodology, or cover letter by the student",
    )


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus = Field(..., description="New application status")


class ApplicationResponse(ApplicationBase):
    id: uuid.UUID
    issue_id: uuid.UUID
    student_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime
    student: Optional[ProfileResponse] = None

    model_config = ConfigDict(from_attributes=True)
