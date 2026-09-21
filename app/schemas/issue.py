from datetime import datetime
from typing import Any, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import IssuePriority, IssueStatus


class IssueMediaBase(BaseModel):
    media_url: str = Field(..., description="Public or storage URL of the media file")
    media_type: str = Field(default="image", description="Type of media (e.g. image, video)")


class IssueMediaCreate(IssueMediaBase):
    pass


class IssueMediaResponse(IssueMediaBase):
    id: uuid.UUID
    issue_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IssueBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, description="Brief summary of the issue")
    description: str = Field(..., min_length=5, description="Detailed description of the issue")
    category: Optional[str] = Field(default=None, description="Issue category (e.g. Infrastructure, Water, Sanitation)")
    priority: Optional[IssuePriority] = Field(default=None, description="Priority level")
    latitude: Optional[float] = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="Geographic latitude coordinate (-90 to +90)",
    )
    longitude: Optional[float] = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="Geographic longitude coordinate (-180 to +180)",
    )
    address: Optional[str] = Field(default=None, max_length=500, description="Textual location or address")


class IssueCreate(IssueBase):
    media_urls: Optional[List[str]] = Field(
        default=None,
        description="Optional list of image/video URLs associated with the issue",
    )


class IssueUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, min_length=5)
    category: Optional[str] = None
    status: Optional[IssueStatus] = None
    priority: Optional[IssuePriority] = None
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    address: Optional[str] = Field(default=None, max_length=500)


class IssueResponse(IssueBase):
    id: uuid.UUID
    reporter_id: uuid.UUID
    assigned_student_id: Optional[uuid.UUID] = None
    category_confidence: Optional[float] = None
    status: str
    priority: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    media: List[IssueMediaResponse] = []

    model_config = ConfigDict(from_attributes=True)


class IssueListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[IssueResponse]


class AssignStudentRequest(BaseModel):
    student_id: uuid.UUID = Field(..., description="UUID of the student to assign")

