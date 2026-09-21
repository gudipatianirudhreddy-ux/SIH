from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_authenticated_user, require_role
from app.database import get_db
from app.models.profile import Profile
from app.schemas.dashboard import (
    CitizenDashboardResponse,
    IndustryDashboardResponse,
    StudentDashboardResponse,
)
from app.services import dashboard as dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/citizen",
    response_model=CitizenDashboardResponse,
    summary="Citizen dashboard overview",
    description="Provides summary metrics of issues reported by the authenticated citizen (total, verified, in-progress, resolved, recent).",
)
def get_citizen_dashboard(
    current_profile: Profile = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_citizen_dashboard_data(
        db=db,
        citizen_id=current_profile.id,
    )


@router.get(
    "/student",
    response_model=StudentDashboardResponse,
    summary="Student dashboard overview",
    description="Provides summary metrics of applications, assigned issues, active issues, and solutions for the authenticated student.",
)
def get_student_dashboard(
    current_profile: Profile = Depends(require_role("STUDENT")),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_student_dashboard_data(
        db=db,
        student_id=current_profile.id,
    )


@router.get(
    "/industry",
    response_model=IndustryDashboardResponse,
    summary="Industry dashboard overview",
    description="Provides summary metrics of available issues, sponsored projects, total funding, and reviewed solutions for industry partners.",
)
def get_industry_dashboard(
    current_profile: Profile = Depends(require_role("INDUSTRY")),
    db: Session = Depends(get_db),
):
    return dashboard_service.get_industry_dashboard_data(
        db=db,
        industrialist_id=current_profile.id,
    )
