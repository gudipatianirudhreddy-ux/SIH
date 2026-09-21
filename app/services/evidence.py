from typing import List, Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.evidence import Evidence
from app.models.issue import Issue
from app.models.profile import Profile
from app.schemas.evidence import EvidenceCreate


def create_evidence(
    db: Session,
    issue_id: uuid.UUID,
    student_profile: Profile,
    evidence_in: EvidenceCreate,
) -> Evidence:
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    # Check that current student is the assigned student on the issue
    if issue.assigned_student_id != student_profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned student can upload progress evidence for this issue",
        )

    db_evidence = Evidence(
        issue_id=issue_id,
        student_id=student_profile.id,
        media_url=evidence_in.media_url,
        description=evidence_in.description,
        evidence_type=evidence_in.evidence_type.value,
    )
    db.add(db_evidence)
    db.commit()
    db.refresh(db_evidence)
    return db_evidence


def list_evidence_for_issue(
    db: Session,
    issue_id: uuid.UUID,
    current_profile: Profile,
) -> List[Evidence]:
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    user_role = (current_profile.role or "").lower()
    is_reporter = issue.reporter_id == current_profile.id
    is_assigned = issue.assigned_student_id == current_profile.id
    is_admin = user_role == "admin"
    is_industry = user_role in ("industry", "industrialist")

    # Authorization: Issue reporter, Assigned student, Industry, Admin
    if not (is_reporter or is_assigned or is_admin or is_industry):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view evidence for this issue",
        )

    return (
        db.query(Evidence)
        .filter(Evidence.issue_id == issue_id)
        .order_by(Evidence.created_at.asc())
        .all()
    )


def delete_evidence(
    db: Session,
    evidence_id: uuid.UUID,
    current_profile: Profile,
) -> None:
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    user_role = (current_profile.role or "").lower()
    is_owner = evidence.student_id == current_profile.id
    is_admin = user_role == "admin"

    if not (is_owner or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this evidence",
        )

    db.delete(evidence)
    db.commit()
