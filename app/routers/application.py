from typing import List
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import require_authenticated_user, require_role
from app.database import get_db
from app.models.profile import Profile
from app.schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationUpdate,
)
from app.schemas.issue import AssignStudentRequest, IssueResponse
from app.services import application as application_service

router = APIRouter(tags=["applications"])


@router.post(
    "/issues/{issue_id}/applications",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply to solve an issue",
    description="Allows an authenticated student to submit an application/proposal for an open, verified societal issue.",
)
def create_application(
    issue_id: uuid.UUID,
    application_in: ApplicationCreate,
    student_profile: Profile = Depends(require_role("STUDENT")),
    db: Session = Depends(get_db),
):
    return application_service.create_application(
        db=db,
        issue_id=issue_id,
        student_id=student_profile.id,
        application_in=application_in,
    )


@router.get(
    "/issues/{issue_id}/applications",
    response_model=List[ApplicationResponse],
    summary="List applications for an issue",
    description="Retrieves applications submitted for an issue. Accessible by issue reporter, industry partners, and administrators.",
)
def list_issue_applications(
    issue_id: uuid.UUID,
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    return application_service.list_applications_for_issue(
        db=db,
        issue_id=issue_id,
        current_profile=current_profile,
    )


@router.get(
    "/applications/me",
    response_model=List[ApplicationResponse],
    summary="Get current student's applications",
    description="Retrieves all issue applications submitted by the authenticated student.",
)
def get_my_applications(
    current_profile: Profile = Depends(require_role("STUDENT")),
    db: Session = Depends(get_db),
):
    return application_service.list_student_applications(
        db=db,
        student_id=current_profile.id,
    )


@router.patch(
    "/applications/{application_id}",
    response_model=ApplicationResponse,
    summary="Update application status",
    description="Allows students to withdraw pending applications, and issue reporters/admins to accept or reject applicants.",
)
def update_application(
    application_id: uuid.UUID,
    application_in: ApplicationUpdate,
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    return application_service.update_application_status(
        db=db,
        application_id=application_id,
        new_status=application_in.status,
        current_profile=current_profile,
    )


@router.post(
    "/issues/{issue_id}/assign",
    response_model=IssueResponse,
    summary="Assign student to issue",
    description="Explicitly assigns an applicant student to work on the issue, transitioning the issue to IN_PROGRESS.",
)
def assign_student(
    issue_id: uuid.UUID,
    assign_in: AssignStudentRequest,
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    return application_service.assign_student_to_issue(
        db=db,
        issue_id=issue_id,
        student_id=assign_in.student_id,
        current_profile=current_profile,
    )
