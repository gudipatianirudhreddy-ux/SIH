from typing import List, Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.collaboration import Collaboration
from app.models.enums import CollaborationStatus, IssueStatus, NotificationType, SolutionStatus
from app.models.issue import Issue
from app.models.solution import Solution, SolutionReview
from app.schemas.solution import SolutionCreate, SolutionReviewCreate, SolutionUpdate
from app.services.notification import create_notification


def create_solution(
    db: Session,
    issue_id: uuid.UUID,
    student_id: uuid.UUID,
    solution_data: SolutionCreate,
) -> Solution:
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    # Assignment verification:
    # If the issue already has an assigned student, only that student can submit
    if issue.assigned_student_id is not None:
        if issue.assigned_student_id != student_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the assigned student can submit a solution for this issue",
            )
    elif issue.status in (IssueStatus.IN_PROGRESS.value, IssueStatus.VERIFIED.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student is not assigned to this issue",
        )
    else:
        # Legacy / unassigned issue backward compatibility: auto-assign student
        issue.assigned_student_id = student_id

    db_solution = Solution(
        issue_id=issue_id,
        student_id=student_id,
        title=solution_data.title,
        description=solution_data.description,
        pdf_url=solution_data.pdf_url,
        prototype_url=solution_data.prototype_url,
        status=SolutionStatus.SUBMITTED.value,
    )
    db.add(db_solution)

    # Automatically transition issue to SOLUTION_SUBMITTED
    issue.status = IssueStatus.SOLUTION_SUBMITTED.value

    db.commit()

    create_notification(
        db=db,
        recipient_id=issue.reporter_id,
        notification_type=NotificationType.SOLUTION_SUBMITTED,
        title="Solution Submitted",
        message=f"A solution '{db_solution.title}' has been submitted for issue '{issue.title}'.",
        issue_id=issue.id,
    )
    active_collab = db.query(Collaboration).filter(
        Collaboration.issue_id == issue.id,
        Collaboration.status == CollaborationStatus.ACTIVE.value,
    ).first()
    if active_collab and active_collab.industrialist_id != issue.reporter_id:
        create_notification(
            db=db,
            recipient_id=active_collab.industrialist_id,
            notification_type=NotificationType.SOLUTION_SUBMITTED,
            title="Solution Submitted",
            message=f"Student has submitted a solution '{db_solution.title}' for collaborated issue '{issue.title}'.",
            issue_id=issue.id,
            collaboration_id=active_collab.id,
        )

    db.refresh(db_solution)
    return db_solution


def get_solution_by_id(db: Session, solution_id: uuid.UUID) -> Optional[Solution]:
    return db.query(Solution).filter(Solution.id == solution_id).first()


def list_solutions_for_issue(db: Session, issue_id: uuid.UUID) -> List[Solution]:
    return (
        db.query(Solution)
        .filter(Solution.issue_id == issue_id)
        .order_by(Solution.created_at.desc())
        .all()
    )


def update_solution(
    db: Session,
    solution: Solution,
    solution_update: SolutionUpdate,
) -> Solution:
    old_status = solution.status
    if solution_update.title is not None:
        solution.title = solution_update.title
    if solution_update.description is not None:
        solution.description = solution_update.description
    if solution_update.pdf_url is not None:
        solution.pdf_url = solution_update.pdf_url
    if solution_update.prototype_url is not None:
        solution.prototype_url = solution_update.prototype_url
    if solution_update.status is not None:
        solution.status = solution_update.status.value

    db.commit()

    if solution_update.status is not None and solution.status != old_status:
        create_notification(
            db=db,
            recipient_id=solution.student_id,
            notification_type=NotificationType.SOLUTION_STATUS_CHANGED,
            title="Solution Status Updated",
            message=f"Your solution '{solution.title}' status changed to {solution.status}.",
            issue_id=solution.issue_id,
        )

    db.refresh(solution)
    return solution


def create_solution_review(
    db: Session,
    solution: Solution,
    reviewer_id: uuid.UUID,
    review_data: SolutionReviewCreate,
) -> SolutionReview:
    db_review = SolutionReview(
        solution_id=solution.id,
        reviewer_id=reviewer_id,
        rating=review_data.rating,
        feedback=review_data.feedback,
    )
    db.add(db_review)

    # Transition solution status to UNDER_REVIEW if currently SUBMITTED
    if solution.status == SolutionStatus.SUBMITTED.value:
        solution.status = SolutionStatus.UNDER_REVIEW.value

    # Transition issue status to EVALUATED if currently in SOLUTION_SUBMITTED
    issue = db.query(Issue).filter(Issue.id == solution.issue_id).first()
    if issue and issue.status == IssueStatus.SOLUTION_SUBMITTED.value:
        issue.status = IssueStatus.EVALUATED.value

    db.commit()
    db.refresh(db_review)
    return db_review


def list_reviews_for_solution(db: Session, solution_id: uuid.UUID) -> List[SolutionReview]:
    return (
        db.query(SolutionReview)
        .filter(SolutionReview.solution_id == solution_id)
        .order_by(SolutionReview.created_at.desc())
        .all()
    )


def list_solutions_for_student(db: Session, student_id: uuid.UUID) -> List[Solution]:
    return (
        db.query(Solution)
        .filter(Solution.student_id == student_id)
        .order_by(Solution.created_at.desc())
        .all()
    )

