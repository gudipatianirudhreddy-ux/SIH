from typing import Optional
from fastapi import HTTPException, status

from app.models.enums import IssueStatus
from app.models.issue import Issue
from app.models.profile import Profile


# Valid forward transitions graph in the core TRANSITION workflow
VALID_TRANSITIONS = {
    IssueStatus.REPORTED.value: {
        IssueStatus.AI_CLASSIFIED.value,
        IssueStatus.VERIFIED.value,
    },
    IssueStatus.AI_CLASSIFIED.value: {
        IssueStatus.VERIFIED.value,
    },
    IssueStatus.VERIFIED.value: {
        IssueStatus.IN_PROGRESS.value,
    },
    IssueStatus.IN_PROGRESS.value: {
        IssueStatus.SOLUTION_SUBMITTED.value,
    },
    IssueStatus.SOLUTION_SUBMITTED.value: {
        IssueStatus.EVALUATED.value,
    },
    IssueStatus.EVALUATED.value: {
        IssueStatus.RESOLVED.value,
    },
    IssueStatus.RESOLVED.value: set(),
}


def can_user_transition_status(
    current_status: str,
    new_status: str,
    profile: Optional[Profile],
    issue: Issue,
) -> bool:
    """Checks if the user possesses the required authorization to transition the issue status."""
    if profile is None:
        return False

    user_role = (profile.role or "").strip().lower()
    is_admin = user_role == "admin"
    is_reporter = issue.reporter_id == profile.id
    is_assigned_student = issue.assigned_student_id == profile.id
    is_industry = user_role in ("industry", "industrialist")

    if is_admin:
        return True

    # REPORTED -> AI_CLASSIFIED: Allowed for reporter or system
    if current_status == IssueStatus.REPORTED.value and new_status == IssueStatus.AI_CLASSIFIED.value:
        return is_reporter

    # REPORTED / AI_CLASSIFIED -> VERIFIED: Reporter or admin verifies issue
    if (
        current_status in (IssueStatus.REPORTED.value, IssueStatus.AI_CLASSIFIED.value)
        and new_status == IssueStatus.VERIFIED.value
    ):
        return is_reporter

    # VERIFIED -> IN_PROGRESS: Reporter or admin assigns student
    if current_status == IssueStatus.VERIFIED.value and new_status == IssueStatus.IN_PROGRESS.value:
        return is_reporter

    # IN_PROGRESS -> SOLUTION_SUBMITTED: Assigned student submits solution
    if current_status == IssueStatus.IN_PROGRESS.value and new_status == IssueStatus.SOLUTION_SUBMITTED.value:
        return is_assigned_student

    # SOLUTION_SUBMITTED -> EVALUATED: Industry mentor or admin evaluates solution
    if current_status == IssueStatus.SOLUTION_SUBMITTED.value and new_status == IssueStatus.EVALUATED.value:
        return is_industry

    # EVALUATED -> RESOLVED: Issue reporter, industry sponsor, or admin confirms resolution
    if current_status == IssueStatus.EVALUATED.value and new_status == IssueStatus.RESOLVED.value:
        return is_reporter or is_industry

    return False


def validate_issue_status_transition(
    issue: Issue,
    new_status: str,
    profile: Optional[Profile] = None,
) -> None:
    """Validates that a status transition follows the valid state machine and the user is authorized.

    Raises:
        HTTPException(400): If transition is invalid in state machine.
        HTTPException(403): If user does not have permission for the transition.
    """
    current_status = issue.status
    if current_status == new_status:
        return

    # Check state machine transition validity
    allowed_targets = VALID_TRANSITIONS.get(current_status, set())
    if new_status not in allowed_targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid status transition from '{current_status}' to '{new_status}'. "
                f"Allowed target statuses: {sorted(list(allowed_targets)) if allowed_targets else 'None (terminal state)'}"
            ),
        )

    # Check caller role / ownership permission
    if profile is not None and not can_user_transition_status(current_status, new_status, profile, issue):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not authorized to transition issue status from '{current_status}' to '{new_status}'",
        )
