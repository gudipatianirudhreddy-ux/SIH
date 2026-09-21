from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EvidenceType


class EvidenceBase(BaseModel):
    media_url: str = Field(..., description="Public or storage URL of progress media/document")
    description: Optional[str] = Field(default=None, description="Progress description, milestone, or notes")
    evidence_type: EvidenceType = Field(
        default=EvidenceType.PROGRESS,
        description="Type of evidence: PROGRESS, BEFORE, AFTER, DOCUMENT, OTHER",
    )


class EvidenceCreate(EvidenceBase):
    pass


class EvidenceResponse(EvidenceBase):
    id: uuid.UUID
    issue_id: uuid.UUID
    student_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
