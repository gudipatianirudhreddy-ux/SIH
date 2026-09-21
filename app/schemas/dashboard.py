from typing import List
from pydantic import BaseModel, ConfigDict

from app.schemas.issue import IssueResponse


class CitizenDashboardResponse(BaseModel):
    total_reported: int
    verified_issues: int
    in_progress_issues: int
    resolved_issues: int
    recent_reported_issues: List[IssueResponse] = []

    model_config = ConfigDict(from_attributes=True)


class StudentDashboardResponse(BaseModel):
    applications_count: int
    accepted_applications: int
    assigned_issues: int
    active_issues: int
    submitted_solutions: int
    selected_or_reviewed_solutions: int
    recent_assigned_issues: List[IssueResponse] = []

    model_config = ConfigDict(from_attributes=True)


class IndustryDashboardResponse(BaseModel):
    issues_available_for_support: int
    sponsored_issues_count: int
    total_sponsored_amount: float
    reviewed_solutions_count: int
    active_supported_projects: int

    model_config = ConfigDict(from_attributes=True)
