from typing import List, Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.enums import ApplicationStatus, IssueStatus, NotificationType
from app.models.issue import Issue
from app.models.profile import Profile
from app.schemas.application import ApplicationCreate
from app.services.notification import create_notification
from app.services.profile import add_points


def create_application(
    db: Session,
    issue_id: uuid.UUID,
    student_id: uuid.UUID,
    application_in: ApplicationCreate,
) -> Application:
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    # Check that issue is in an application-eligible state (must be VERIFIED)
    if issue.status != IssueStatus.VERIFIED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Applications are only open for issues with status 'VERIFIED' (current status: '{issue.status}')",
        )

    # Check if student already applied
    existing = (
        db.query(Application)
        .filter(
            Application.issue_id == issue_id,
            Application.student_id == student_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student has already submitted an application for this issue",
        )

    db_application = Application(
        issue_id=issue_id,
        student_id=student_id,
        proposal=application_in.proposal,
        status=ApplicationStatus.PENDING.value,
    )
    db.add(db_application)
    db.commit()

    create_notification(
        db=db,
        recipient_id=issue.reporter_id,
        notification_type=NotificationType.APPLICATION_SUBMITTED,
        title="New Proposal Submitted",
        message=f"A student has submitted a proposal for your issue '{issue.title}'.",
        issue_id=issue.id,
        application_id=db_application.id,
    )

    db.refresh(db_application)
    return db_application


def get_application_by_id(db: Session, application_id: uuid.UUID) -> Optional[Application]:
    return db.query(Application).filter(Application.id == application_id).first()


def list_applications_for_issue(
    db: Session,
    issue_id: uuid.UUID,
    current_profile: Profile,
) -> List[Application]:
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    user_role = (current_profile.role or "").lower()
    is_reporter = issue.reporter_id == current_profile.id
    is_admin = user_role == "admin"
    is_industry = user_role in ("industry", "industrialist")

    # Authorization: Issue reporter, Admin, Industry
    if not (is_reporter or is_admin or is_industry):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view applications for this issue",
        )

    return (
        db.query(Application)
        .filter(Application.issue_id == issue_id)
        .order_by(Application.created_at.desc())
        .all()
    )


def list_student_applications(
    db: Session,
    student_id: uuid.UUID,
) -> List[Application]:
    return (
        db.query(Application)
        .filter(Application.student_id == student_id)
        .order_by(Application.created_at.desc())
        .all()
    )


def update_application_status(
    db: Session,
    application_id: uuid.UUID,
    new_status: ApplicationStatus,
    current_profile: Profile,
) -> Application:
    application = get_application_by_id(db, application_id)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    issue = db.query(Issue).filter(Issue.id == application.issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated issue not found",
        )

    user_role = (current_profile.role or "").lower()
    is_student_owner = application.student_id == current_profile.id
    is_reporter = issue.reporter_id == current_profile.id
    is_admin = user_role == "admin"

    # Rule 1: A student should NOT be able to accept their own application
    if new_status == ApplicationStatus.ACCEPTED:
        if is_student_owner and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students cannot accept their own application",
            )
        if not (is_reporter or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the issue reporter or an admin can accept an application",
            )

    # Rule 2: A student may withdraw their own pending application
    elif new_status == ApplicationStatus.WITHDRAWN:
        if not (is_student_owner or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the student applicant can withdraw their application",
            )

    # Selection must go through the Industrialist collaboration endpoint.
    elif new_status == ApplicationStatus.SELECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use the Industrialist proposal selection endpoint to select an application",
        )

    # Rule 3: Rejecting an application
    elif new_status == ApplicationStatus.REJECTED:
        if not (is_reporter or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the issue reporter or an admin can reject an application",
            )

    was_already_accepted = application.status == ApplicationStatus.ACCEPTED.value
    application.status = new_status.value

    # When an application is accepted:
    # 1. Automatically assign that student to the issue.
    # 2. Reject other pending applications for the same issue.
    # 3. Update issue status to IN_PROGRESS.
    if new_status == ApplicationStatus.ACCEPTED:
        issue.assigned_student_id = application.student_id
        issue.status = IssueStatus.IN_PROGRESS.value

        other_pending = (
            db.query(Application)
            .filter(
                Application.issue_id == issue.id,
                Application.id != application.id,
                Application.status == ApplicationStatus.PENDING.value,
            )
            .all()
        )
        for other in other_pending:
            other.status = ApplicationStatus.REJECTED.value
            create_notification(
                db=db,
                recipient_id=other.student_id,
                notification_type=NotificationType.APPLICATION_REJECTED,
                title="Proposal Rejected",
                message=f"Your proposal for issue '{issue.title}' has been rejected as another applicant was accepted.",
                issue_id=issue.id,
                application_id=other.id,
            )
        if not was_already_accepted:
            add_points(db, application.student_id, 10, "ISSUE_TAKEN", issue.id)

        create_notification(
            db=db,
            recipient_id=application.student_id,
            notification_type=NotificationType.APPLICATION_ACCEPTED,
            title="Proposal Accepted",
            message=f"Your proposal for issue '{issue.title}' has been accepted!",
            issue_id=issue.id,
            application_id=application.id,
        )

    elif new_status == ApplicationStatus.REJECTED:
        create_notification(
            db=db,
            recipient_id=application.student_id,
            notification_type=NotificationType.APPLICATION_REJECTED,
            title="Proposal Rejected",
            message=f"Your proposal for issue '{issue.title}' has been rejected.",
            issue_id=issue.id,
            application_id=application.id,
        )

    db.commit()
    db.refresh(application)
    db.refresh(issue)
    return application


def assign_student_to_issue(
    db: Session,
    issue_id: uuid.UUID,
    student_id: uuid.UUID,
    current_profile: Profile,
) -> Issue:
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    user_role = (current_profile.role or "").lower()
    is_reporter = issue.reporter_id == current_profile.id
    is_admin = user_role == "admin"
    if not (is_reporter or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the issue reporter or an admin can assign a student to this issue",
        )

    # Verify student has an application for the issue
    app_record = (
        db.query(Application)
        .filter(
            Application.issue_id == issue_id,
            Application.student_id == student_id,
        )
        .first()
    )
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student has not applied for this issue",
        )

    # Accept the student's application if pending
    was_already_accepted = app_record.status == ApplicationStatus.ACCEPTED.value
    app_record.status = ApplicationStatus.ACCEPTED.value

    # Reject other pending applications
    other_pending = (
        db.query(Application)
        .filter(
            Application.issue_id == issue.id,
            Application.id != app_record.id,
            Application.status == ApplicationStatus.PENDING.value,
        )
        .all()
    )
    for other in other_pending:
        other.status = ApplicationStatus.REJECTED.value
        create_notification(
            db=db,
            recipient_id=other.student_id,
            notification_type=NotificationType.APPLICATION_REJECTED,
            title="Proposal Rejected",
            message=f"Your proposal for issue '{issue.title}' has been rejected as another student was assigned.",
            issue_id=issue.id,
            application_id=other.id,
        )

    # Assign student and update status to IN_PROGRESS
    issue.assigned_student_id = student_id
    issue.status = IssueStatus.IN_PROGRESS.value
    if not was_already_accepted:
        add_points(db, student_id, 10, "ISSUE_TAKEN", issue.id)

    create_notification(
        db=db,
        recipient_id=student_id,
        notification_type=NotificationType.APPLICATION_ACCEPTED,
        title="Assigned to Issue",
        message=f"You have been assigned to work on issue '{issue.title}'.",
        issue_id=issue.id,
        application_id=app_record.id,
    )

    db.commit()
    db.refresh(issue)
    return issue
