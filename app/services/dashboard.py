from typing import Any, Dict
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.enums import ApplicationStatus, IssueStatus, SolutionStatus, SponsorshipStatus
from app.models.issue import Issue
from app.models.solution import Solution, SolutionReview
from app.models.sponsorship import Sponsorship


def get_citizen_dashboard_data(db: Session, citizen_id: uuid.UUID) -> Dict[str, Any]:
    """Lightweight aggregated metrics for Citizen role."""
    base_query = db.query(Issue).filter(Issue.reporter_id == citizen_id)

    total_reported = base_query.count()
    verified_issues = base_query.filter(Issue.status == IssueStatus.VERIFIED.value).count()
    in_progress_issues = base_query.filter(Issue.status == IssueStatus.IN_PROGRESS.value).count()
    resolved_issues = base_query.filter(Issue.status == IssueStatus.RESOLVED.value).count()

    recent_issues = (
        base_query.order_by(Issue.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "total_reported": total_reported,
        "verified_issues": verified_issues,
        "in_progress_issues": in_progress_issues,
        "resolved_issues": resolved_issues,
        "recent_reported_issues": recent_issues,
    }


def get_student_dashboard_data(db: Session, student_id: uuid.UUID) -> Dict[str, Any]:
    """Lightweight aggregated metrics for Student role."""
    apps_query = db.query(Application).filter(Application.student_id == student_id)
    applications_count = apps_query.count()
    accepted_applications = apps_query.filter(
        Application.status == ApplicationStatus.ACCEPTED.value
    ).count()

    assigned_query = db.query(Issue).filter(Issue.assigned_student_id == student_id)
    assigned_issues = assigned_query.count()
    active_issues = assigned_query.filter(
        Issue.status == IssueStatus.IN_PROGRESS.value
    ).count()

    solutions_query = db.query(Solution).filter(Solution.student_id == student_id)
    submitted_solutions = solutions_query.count()

    selected_or_reviewed = (
        solutions_query.filter(
            (Solution.status.in_([SolutionStatus.SELECTED.value, SolutionStatus.SHORTLISTED.value]))
            | (Solution.reviews.any())
        ).count()
    )

    recent_assigned = (
        assigned_query.order_by(Issue.updated_at.desc())
        .limit(5)
        .all()
    )

    return {
        "applications_count": applications_count,
        "accepted_applications": accepted_applications,
        "assigned_issues": assigned_issues,
        "active_issues": active_issues,
        "submitted_solutions": submitted_solutions,
        "selected_or_reviewed_solutions": selected_or_reviewed,
        "recent_assigned_issues": recent_assigned,
    }


def get_industry_dashboard_data(db: Session, industrialist_id: uuid.UUID) -> Dict[str, Any]:
    """Lightweight aggregated metrics for Industry role."""
    # Issues available for review or funding (VERIFIED, IN_PROGRESS, SOLUTION_SUBMITTED)
    available_issues_count = (
        db.query(Issue)
        .filter(
            Issue.status.in_([
                IssueStatus.VERIFIED.value,
                IssueStatus.IN_PROGRESS.value,
                IssueStatus.SOLUTION_SUBMITTED.value,
            ])
        )
        .count()
    )

    sponsorships_query = db.query(Sponsorship).filter(
        Sponsorship.industrialist_id == industrialist_id
    )
    sponsored_issues_count = sponsorships_query.count()

    total_amount = (
        db.query(func.coalesce(func.sum(Sponsorship.amount), 0.0))
        .filter(
            Sponsorship.industrialist_id == industrialist_id,
            Sponsorship.status.in_([SponsorshipStatus.PLEDGED.value, SponsorshipStatus.APPROVED.value]),
        )
        .scalar()
    ) or 0.0

    reviewed_count = (
        db.query(SolutionReview)
        .filter(SolutionReview.reviewer_id == industrialist_id)
        .count()
    )

    active_supported_projects = (
        db.query(Issue)
        .join(Sponsorship, Sponsorship.issue_id == Issue.id)
        .filter(
            Sponsorship.industrialist_id == industrialist_id,
            Issue.status != IssueStatus.RESOLVED.value,
        )
        .distinct()
        .count()
    )

    return {
        "issues_available_for_support": available_issues_count,
        "sponsored_issues_count": sponsored_issues_count,
        "total_sponsored_amount": float(total_amount),
        "reviewed_solutions_count": reviewed_count,
        "active_supported_projects": active_supported_projects,
    }
