from typing import List, Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import IssueStatus, SolutionStatus
from app.models.issue import Issue
from app.models.solution import Solution, SolutionReview
from app.schemas.solution import SolutionCreate, SolutionReviewCreate, SolutionUpdate


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

    # Automatically transition issue to SOLUTION_SUBMITTED if active
    if issue.status in (
        IssueStatus.REPORTED.value,
        IssueStatus.AI_CLASSIFIED.value,
        IssueStatus.VERIFIED.value,
        IssueStatus.IN_PROGRESS.value,
    ):
        issue.status = IssueStatus.SOLUTION_SUBMITTED.value

    db.commit()
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
