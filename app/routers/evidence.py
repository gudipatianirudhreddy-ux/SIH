from typing import List
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import require_authenticated_user, require_role
from app.database import get_db
from app.models.profile import Profile
from app.schemas.evidence import EvidenceCreate, EvidenceResponse
from app.services import evidence as evidence_service

router = APIRouter(tags=["evidence"])


@router.post(
    "/issues/{issue_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload progress/evidence for an issue",
    description="Allows the assigned student to upload progress milestones, before/after media, or documentation for an issue.",
)
def create_evidence(
    issue_id: uuid.UUID,
    evidence_in: EvidenceCreate,
    student_profile: Profile = Depends(require_role("STUDENT")),
    db: Session = Depends(get_db),
):
    return evidence_service.create_evidence(
        db=db,
        issue_id=issue_id,
        student_profile=student_profile,
        evidence_in=evidence_in,
    )


@router.get(
    "/issues/{issue_id}/evidence",
    response_model=List[EvidenceResponse],
    summary="List evidence for an issue",
    description="Retrieves progress evidence and documentation for an issue. Accessible by reporter, assigned student, industry partners, and admins.",
)
def list_issue_evidence(
    issue_id: uuid.UUID,
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    return evidence_service.list_evidence_for_issue(
        db=db,
        issue_id=issue_id,
        current_profile=current_profile,
    )


@router.delete(
    "/evidence/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete evidence",
    description="Deletes an evidence record. Permitted for the evidence author or an administrator.",
)
def delete_evidence(
    evidence_id: uuid.UUID,
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    evidence_service.delete_evidence(
        db=db,
        evidence_id=evidence_id,
        current_profile=current_profile,
    )
    return None
