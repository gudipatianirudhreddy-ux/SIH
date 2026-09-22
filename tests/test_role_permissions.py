import uuid
import pytest
from fastapi import status

from app.auth import get_current_user
from app.main import app
from app.models.enums import IssueStatus
from tests.conftest import MockUser


def _create_user(client, role: str, name: str) -> str:
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)
    res = client.post("/profiles/me", json={"name": name, "role": role})
    assert res.status_code == status.HTTP_201_CREATED
    return user_id


def _create_verified_issue(client, reporter_id: str) -> str:
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=reporter_id)
    issue_res = client.post(
        "/issues",
        json={"title": "Verified Infrastructure Issue", "description": "Needs bridge repair"},
    )
    assert issue_res.status_code == status.HTTP_201_CREATED
    issue_id = issue_res.json()["id"]

    verify_res = client.patch(f"/issues/{issue_id}", json={"status": IssueStatus.VERIFIED.value})
    assert verify_res.status_code == status.HTTP_200_OK
    return issue_id


# ==============================================================================
# STUDENT APPLICATION PERMISSIONS
# ==============================================================================

def test_student_can_apply_to_verified_issue(client):
    """Student is permitted to submit an application to a verified issue."""
    reporter_id = _create_user(client, role="citizen", name="Perm Reporter")
    student_id = _create_user(client, role="student", name="Perm Student")
    issue_id = _create_verified_issue(client, reporter_id)

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    res = client.post(
        f"/issues/{issue_id}/applications",
        json={"proposal": "Structural damping simulation using ANSYS"},
    )
    assert res.status_code == status.HTTP_201_CREATED
    assert res.json()["student_id"] == student_id


def test_citizen_cannot_use_student_application_endpoint(client):
    """Citizen role is rejected (403 Forbidden) when attempting to apply to an issue."""
    reporter_id = _create_user(client, role="citizen", name="Perm Reporter 2")
    citizen_applicant_id = _create_user(client, role="citizen", name="Eager Citizen")
    issue_id = _create_verified_issue(client, reporter_id)

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_applicant_id)
    res = client.post(
        f"/issues/{issue_id}/applications",
        json={"proposal": "I want to apply as citizen"},
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "Required role" in res.json()["detail"]


def test_industrialist_cannot_use_student_application_endpoint(client):
    """Industrialist role is rejected (403 Forbidden) when attempting to apply to an issue."""
    reporter_id = _create_user(client, role="citizen", name="Perm Reporter 3")
    industry_id = _create_user(client, role="industrialist", name="Industry Corp")
    issue_id = _create_verified_issue(client, reporter_id)

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=industry_id)
    res = client.post(
        f"/issues/{issue_id}/applications",
        json={"proposal": "Industry applying as student"},
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "Required role" in res.json()["detail"]


# ==============================================================================
# SOLUTION SUBMISSION PERMISSIONS
# ==============================================================================

def test_student_can_submit_solution(client):
    """Student is permitted to submit a solution for an issue where appropriate."""
    reporter_id = _create_user(client, role="citizen", name="Sol Reporter")
    student_id = _create_user(client, role="student", name="Sol Student")

    # Reporter creates issue (REPORTED status allows student solution / auto-assign)
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=reporter_id)
    issue_res = client.post(
        "/issues",
        json={"title": "Low-Cost Filtration Needed", "description": "Community water purification problem"},
    )
    assert issue_res.status_code == status.HTTP_201_CREATED
    issue_id = issue_res.json()["id"]

    # Student submits solution
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    sol_payload = {
        "title": "Low-Cost Filtration Unit",
        "description": "Multi-stage sand and activated carbon filtration with gravity flow.",
    }
    res = client.post(f"/issues/{issue_id}/solutions", json=sol_payload)
    assert res.status_code == status.HTTP_201_CREATED
    assert res.json()["student_id"] == student_id
    assert res.json()["status"] == "SUBMITTED"


def test_citizen_cannot_submit_solution(client):
    """Citizen role receives 403 Forbidden when attempting to submit a solution."""
    reporter_id = _create_user(client, role="citizen", name="Sol Reporter 2")
    citizen_id = _create_user(client, role="citizen", name="Citizen Sol")
    issue_id = _create_verified_issue(client, reporter_id)

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    res = client.post(
        f"/issues/{issue_id}/solutions",
        json={"title": "Citizen Solution", "description": "Direct citizen submission"},
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_industrialist_cannot_submit_solution(client):
    """Industrialist role receives 403 Forbidden when attempting to submit a solution."""
    reporter_id = _create_user(client, role="citizen", name="Sol Reporter 3")
    industry_id = _create_user(client, role="industrialist", name="Industry Sol")
    issue_id = _create_verified_issue(client, reporter_id)

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=industry_id)
    res = client.post(
        f"/issues/{issue_id}/solutions",
        json={"title": "Industry Solution", "description": "Company solution submission"},
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# INDUSTRY SPONSORSHIP PERMISSIONS
# ==============================================================================

def test_industrialist_can_pledge_sponsorship(client):
    """Industrialist is permitted to pledge sponsorship for an issue."""
    reporter_id = _create_user(client, role="citizen", name="Sponsor Reporter")
    industry_id = _create_user(client, role="industrialist", name="Tech Foundation")
    issue_id = _create_verified_issue(client, reporter_id)

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=industry_id)
    sponsorship_payload = {
        "amount": 250000.0,
        "message": "Grant allocated for renewable energy hardware components",
    }
    res = client.post(f"/issues/{issue_id}/sponsorships", json=sponsorship_payload)
    assert res.status_code == status.HTTP_201_CREATED
    assert res.json()["industrialist_id"] == industry_id
    assert res.json()["amount"] == 250000.0
    assert res.json()["message"] == sponsorship_payload["message"]


def test_citizen_cannot_pledge_sponsorship(client):
    """Citizen role receives 403 Forbidden when attempting to pledge sponsorship."""
    reporter_id = _create_user(client, role="citizen", name="Sponsor Reporter 2")
    citizen_id = _create_user(client, role="citizen", name="Citizen Sponsor")
    issue_id = _create_verified_issue(client, reporter_id)

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    res = client.post(
        f"/issues/{issue_id}/sponsorships",
        json={"amount": 1000.0, "sponsorship_type": "donation"},
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "Required role" in res.json()["detail"]


def test_student_cannot_pledge_sponsorship(client):
    """Student role receives 403 Forbidden when attempting to pledge sponsorship."""
    reporter_id = _create_user(client, role="citizen", name="Sponsor Reporter 3")
    student_id = _create_user(client, role="student", name="Student Sponsor")
    issue_id = _create_verified_issue(client, reporter_id)

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    res = client.post(
        f"/issues/{issue_id}/sponsorships",
        json={"amount": 5000.0, "sponsorship_type": "materials"},
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert "Required role" in res.json()["detail"]


# ==============================================================================
# STUDENT-ONLY CONVENIENCE ENDPOINTS
# ==============================================================================

def test_student_only_queries_reject_citizen_and_industrialist(client):
    """Endpoints like /applications/me and /issues/me/solutions reject non-students."""
    citizen_id = _create_user(client, role="citizen", name="Non Student Citizen")
    industry_id = _create_user(client, role="industrialist", name="Non Student Industry")

    for user_id in [citizen_id, industry_id]:
        app.dependency_overrides[get_current_user] = lambda u=user_id: MockUser(u)
        res_apps = client.get("/applications/me")
        assert res_apps.status_code == status.HTTP_403_FORBIDDEN
        res_sols = client.get("/issues/me/solutions")
        assert res_sols.status_code == status.HTTP_403_FORBIDDEN
