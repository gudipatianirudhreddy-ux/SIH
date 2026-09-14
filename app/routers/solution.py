from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import require_authenticated_user, require_role
from app.database import get_db
from app.models.profile import Profile
from app.schemas.solution import (
    SolutionCreate,
    SolutionResponse,
    SolutionReviewCreate,
    SolutionReviewResponse,
    SolutionUpdate,
)
from app.services import solution as solution_service

router = APIRouter(tags=["solutions"])


@router.post(
    "/issues/{issue_id}/solutions",
    response_model=SolutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a solution for an issue",
    description="Allows an authenticated student to submit a solution/prototype for a societal issue.",
)
def create_solution(
    issue_id: uuid.UUID,
    solution_in: SolutionCreate,
    student_profile: Profile = Depends(require_role("STUDENT")),
    db: Session = Depends(get_db),
):
    return solution_service.create_solution(
        db=db,
        issue_id=issue_id,
        student_id=student_profile.id,
        solution_data=solution_in,
    )


@router.get(
    "/issues/{issue_id}/solutions",
    response_model=List[SolutionResponse],
    summary="List solutions for an issue",
    description="Retrieves all student-submitted solutions and proposals for a specific issue.",
)
def list_issue_solutions(
    issue_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    return solution_service.list_solutions_for_issue(db, issue_id)


@router.get(
    "/solutions/{solution_id}",
    response_model=SolutionResponse,
    summary="Get solution details",
    description="Retrieves details for a specific solution, including submitted prototypes and industry reviews.",
)
def get_solution(
    solution_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    solution = solution_service.get_solution_by_id(db, solution_id)
    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solution not found",
        )
    return solution


@router.patch(
    "/solutions/{solution_id}",
    response_model=SolutionResponse,
    summary="Update a solution",
    description="Updates a solution's content or status. Content edits require student owner; status updates permitted for industry or admin.",
)
def update_solution(
    solution_id: uuid.UUID,
    solution_in: SolutionUpdate,
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    solution = solution_service.get_solution_by_id(db, solution_id)
    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solution not found",
        )

    user_role = (current_profile.role or "").lower()
    is_owner = solution.student_id == current_profile.id
    is_industry_or_admin = user_role in ("industry", "industrialist", "admin")

    # If updating content fields (title, description, pdf_url, prototype_url), require owner or admin
    is_editing_content = any(
        v is not None
        for v in [
            solution_in.title,
            solution_in.description,
            solution_in.pdf_url,
            solution_in.prototype_url,
        ]
    )
    if is_editing_content and not (is_owner or user_role == "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the student owner can modify solution details",
        )

    # If updating status only, allowed for owner, industry, or admin
    if solution_in.status is not None and not (is_owner or is_industry_or_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update the status of this solution",
        )

    return solution_service.update_solution(db, solution, solution_in)


@router.post(
    "/solutions/{solution_id}/reviews",
    response_model=SolutionReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit industry feedback/review for a solution",
    description="Allows industry mentors and administrators to review a student solution, provide constructive feedback, and submit an optional rating.",
)
def create_solution_review(
    solution_id: uuid.UUID,
    review_in: SolutionReviewCreate,
    industry_profile: Profile = Depends(require_role("INDUSTRY")),
    db: Session = Depends(get_db),
):
    solution = solution_service.get_solution_by_id(db, solution_id)
    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solution not found",
        )

    return solution_service.create_solution_review(
        db=db,
        solution=solution,
        reviewer_id=industry_profile.id,
        review_data=review_in,
    )


@router.get(
    "/solutions/{solution_id}/reviews",
    response_model=List[SolutionReviewResponse],
    summary="List reviews for a solution",
    description="Retrieves all industry feedback and ratings submitted for a solution.",
)
def list_solution_reviews(
    solution_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    solution = solution_service.get_solution_by_id(db, solution_id)
    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solution not found",
        )
    return solution_service.list_reviews_for_solution(db, solution_id)
