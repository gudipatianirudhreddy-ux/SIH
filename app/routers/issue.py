from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import require_authenticated_user, require_role
from app.database import get_db
from app.models.profile import Profile
from app.schemas.issue import (
    IssueCreate,
    IssueListResponse,
    IssueMediaCreate,
    IssueMediaResponse,
    IssueResponse,
    IssueUpdate,
)
from app.services import issue as issue_service

router = APIRouter(prefix="/issues", tags=["issues"])


@router.post(
    "",
    response_model=IssueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report a new societal issue",
    description="Creates a new societal issue reported by any authenticated stakeholder (Citizen, Student, or Industrialist). If media URLs are attached, automated ML classification is triggered.",
)
def create_issue(
    issue_in: IssueCreate,
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    return issue_service.create_issue(
        db=db,
        reporter_id=current_profile.id,
        issue_data=issue_in,
    )


@router.get(
    "",
    response_model=IssueListResponse,
    summary="List and filter societal issues",
    description="Retrieves a paginated list of reported issues, sorted with newest first. Supports filtering by category, status, and geographic bounding coordinates.",
)
def list_issues(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(default=None, description="Filter by problem category"),
    status: Optional[str] = Query(default=None, description="Filter by issue status"),
    min_lat: Optional[float] = Query(default=None, ge=-90.0, le=90.0, description="Min latitude bounding"),
    max_lat: Optional[float] = Query(default=None, ge=-90.0, le=90.0, description="Max latitude bounding"),
    min_lon: Optional[float] = Query(default=None, ge=-180.0, le=180.0, description="Min longitude bounding"),
    max_lon: Optional[float] = Query(default=None, ge=-180.0, le=180.0, description="Max longitude bounding"),
    db: Session = Depends(get_db),
):
    items, total = issue_service.list_issues(
        db=db,
        page=page,
        page_size=page_size,
        category=category,
        status=status,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
    )
    return IssueListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get(
    "/nearby",
    response_model=IssueListResponse,
    summary="List nearby societal issues",
    description="Returns issues within a radius of the supplied coordinates. Defaults to a 5 km radius.",
)
def get_nearby_issues(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Current latitude"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Current longitude"),
    radius_km: float = Query(default=5.0, gt=0.0, le=50.0, description="Search radius in kilometers"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = issue_service.list_nearby_issues(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        page=page,
        page_size=page_size,
    )
    return IssueListResponse(total=total, page=page, page_size=page_size, items=items)


@router.get(
    "/me/reported",
    response_model=IssueListResponse,
    summary="Get issues reported by the current user",
    description="Retrieves a paginated list of societal issues reported by the authenticated user.",
)
def get_my_reported_issues(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    items, total = issue_service.list_reported_issues(
        db=db,
        reporter_id=current_profile.id,
        page=page,
        page_size=page_size,
    )
    return IssueListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get(
    "/me/assigned",
    response_model=IssueListResponse,
    summary="Get issues assigned to current student",
    description="Retrieves a paginated list of societal issues assigned to the authenticated student.",
)
def get_my_assigned_issues(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_profile: Profile = Depends(require_role("STUDENT")),
    db: Session = Depends(get_db),
):
    items, total = issue_service.list_assigned_issues(
        db=db,
        student_id=current_profile.id,
        page=page,
        page_size=page_size,
    )
    return IssueListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get(
    "/{issue_id}",
    response_model=IssueResponse,
    summary="Get detailed issue by ID",
    description="Retrieves complete information about a specific societal issue, including its attached media and metadata.",
)
def get_issue(
    issue_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    issue = issue_service.get_issue_by_id(db, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )
    return issue


@router.patch(
    "/{issue_id}",
    response_model=IssueResponse,
    summary="Update an issue",
    description="Updates issue details. Only the original reporter or an administrator is authorized to edit the issue.",
)
def update_issue(
    issue_id: uuid.UUID,
    issue_in: IssueUpdate,
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    issue = issue_service.get_issue_by_id(db, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    # Ownership / authorization check
    is_reporter = issue.reporter_id == current_profile.id
    is_admin = (current_profile.role or "").lower() == "admin"
    if not (is_reporter or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this issue",
        )

    return issue_service.update_issue(db, issue, issue_in, profile=current_profile)



@router.delete(
    "/{issue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an issue",
    description="Deletes an issue. Only the original reporter or an administrator is authorized to perform this deletion.",
)
def delete_issue(
    issue_id: uuid.UUID,
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    issue = issue_service.get_issue_by_id(db, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    is_reporter = issue.reporter_id == current_profile.id
    is_admin = (current_profile.role or "").lower() == "admin"
    if not (is_reporter or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this issue",
        )

    issue_service.delete_issue(db, issue)
    return None


@router.post(
    "/{issue_id}/media",
    response_model=IssueMediaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach media to an issue",
    description="Attaches an image or video URL to an issue and triggers ML categorization if category is not yet determined.",
)
def attach_media(
    issue_id: uuid.UUID,
    media_in: IssueMediaCreate,
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    issue = issue_service.get_issue_by_id(db, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found",
        )

    is_reporter = issue.reporter_id == current_profile.id
    is_admin = (current_profile.role or "").lower() == "admin"
    if not (is_reporter or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to attach media to this issue",
        )

    return issue_service.add_media_to_issue(
        db=db,
        issue=issue,
        media_url=media_in.media_url,
        media_type=media_in.media_type,
    )
