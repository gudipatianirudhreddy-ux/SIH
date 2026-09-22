import uuid
import pytest
from fastapi import status

from app.auth import get_current_user
from app.main import app
from app.models.enums import ApplicationStatus, IssueStatus
from app.models.point_transaction import PointTransaction
from app.models.profile import Profile
from tests.conftest import MockUser


def _create_profile(client, role: str, name: str) -> str:
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)
    res = client.post("/profiles/me", json={"name": name, "role": role})
    assert res.status_code == status.HTTP_201_CREATED
    return user_id


# ==============================================================================
# ISSUE REPORTING REWARDS TESTS
# ==============================================================================

@pytest.mark.parametrize("role", ["citizen", "student", "industrialist"])
def test_issue_reporting_reward_all_roles(client, db_session, role):
    """Citizen, Student, and Industrialist each receive +10 points and ISSUE_REPORTED tx on reporting an issue."""
    user_id = _create_profile(client, role=role, name=f"Reporter {role.capitalize()}")

    # Check baseline balance (50 welcome points)
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)
    initial_pts_res = client.get("/points/me")
    assert initial_pts_res.json()["points"] == 50

    # Report an issue
    issue_payload = {
        "title": f"Broken Pipeline reported by {role}",
        "description": "Clean water leakage observed near market intersection",
        "latitude": 12.9716,
        "longitude": 77.5946,
    }
    issue_res = client.post("/issues", json=issue_payload)
    assert issue_res.status_code == status.HTTP_201_CREATED
    issue_data = issue_res.json()
    issue_id = issue_data["id"]

    # Check updated balance: 50 + 10 = 60
    pts_res = client.get("/points/me")
    pts_data = pts_res.json()
    assert pts_data["points"] == 60

    # Verify transactions in /points/me
    txs = pts_data["transactions"]
    assert len(txs) == 2
    reported_tx = next((t for t in txs if t["reason"] == "ISSUE_REPORTED"), None)
    assert reported_tx is not None
    assert reported_tx["points"] == 10
    assert reported_tx["issue_id"] == issue_id
    assert reported_tx["user_id"] == user_id

    # Verify database directly
    profile = db_session.query(Profile).filter(Profile.id == uuid.UUID(user_id)).first()
    assert profile.points == 60
    db_tx = (
        db_session.query(PointTransaction)
        .filter(
            PointTransaction.user_id == uuid.UUID(user_id),
            PointTransaction.reason == "ISSUE_REPORTED",
        )
        .first()
    )
    assert db_tx is not None
    assert str(db_tx.issue_id) == issue_id


def test_reporting_multiple_issues_awards_points_for_each(client, db_session):
    """Reporting multiple valid issues increments points by 10 for each report with separate transactions."""
    user_id = _create_profile(client, role="citizen", name="Active Citizen")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    created_issue_ids = []
    for i in range(3):
        res = client.post(
            "/issues",
            json={
                "title": f"Issue Number {i + 1}",
                "description": f"Detailed description for issue number {i + 1}",
            },
        )
        assert res.status_code == status.HTTP_201_CREATED
        created_issue_ids.append(res.json()["id"])

    # Initial (50) + 3 * 10 = 80 points
    pts_res = client.get("/points/me")
    assert pts_res.json()["points"] == 80

    # Check that 3 distinct ISSUE_REPORTED transactions exist with proper issue_id links
    reported_txs = [t for t in pts_res.json()["transactions"] if t["reason"] == "ISSUE_REPORTED"]
    assert len(reported_txs) == 3
    linked_ids = {t["issue_id"] for t in reported_txs}
    assert linked_ids == set(created_issue_ids)


def test_issue_reward_not_duplicated_on_patch_or_get(client):
    """Updating or viewing an issue does not award additional points."""
    user_id = _create_profile(client, role="citizen", name="Careful Citizen")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    res = client.post("/issues", json={"title": "Pothole Main Rd", "description": "Big pothole on road"})
    assert res.status_code == status.HTTP_201_CREATED
    issue_id = res.json()["id"]

    pts_after_create = client.get("/points/me").json()["points"]
    assert pts_after_create == 60

    # Patch issue title
    client.patch(f"/issues/{issue_id}", json={"title": "Updated Pothole Main Rd"})
    assert client.get("/points/me").json()["points"] == 60

    # Get issue details
    client.get(f"/issues/{issue_id}")
    assert client.get("/points/me").json()["points"] == 60


# ==============================================================================
# STUDENT ASSIGNMENT REWARD TESTS
# ==============================================================================

def test_student_accepted_application_reward(client, db_session):
    """A student whose application is accepted receives +10 points with reason ISSUE_TAKEN linked to issue."""
    reporter_id = _create_profile(client, role="citizen", name="Issue Reporter")
    student_id = _create_profile(client, role="student", name="Applicant Student")

    # Reporter creates issue
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=reporter_id)
    issue_res = client.post("/issues", json={"title": "Smart Solar Lamp", "description": "Need street lighting"})
    issue_id = issue_res.json()["id"]

    # Reporter marks issue VERIFIED
    verify_res = client.patch(f"/issues/{issue_id}", json={"status": IssueStatus.VERIFIED.value})
    assert verify_res.status_code == status.HTTP_200_OK

    # Student applies
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    app_res = client.post(
        f"/issues/{issue_id}/applications",
        json={"proposal": "I have an efficient circuit design"},
    )
    assert app_res.status_code == status.HTTP_201_CREATED
    application_id = app_res.json()["id"]

    # Baseline student points before acceptance: 50
    assert client.get("/points/me").json()["points"] == 50

    # Reporter accepts the student's application
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=reporter_id)
    accept_res = client.patch(
        f"/applications/{application_id}",
        json={"status": ApplicationStatus.ACCEPTED.value},
    )
    assert accept_res.status_code == status.HTTP_200_OK

    # Check student points: 50 + 10 = 60
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    stu_pts = client.get("/points/me").json()
    assert stu_pts["points"] == 60

    taken_tx = next((t for t in stu_pts["transactions"] if t["reason"] == "ISSUE_TAKEN"), None)
    assert taken_tx is not None
    assert taken_tx["points"] == 10
    assert taken_tx["issue_id"] == issue_id
    assert taken_tx["user_id"] == student_id


def test_student_assigned_via_assign_endpoint_reward(client, db_session):
    """Assigning student via POST /issues/{issue_id}/assign awards +10 points to student."""
    reporter_id = _create_profile(client, role="citizen", name="Assigning Reporter")
    student_id = _create_profile(client, role="student", name="Assigned Student")

    # Reporter creates issue
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=reporter_id)
    issue_res = client.post("/issues", json={"title": "Traffic Sensor", "description": "Congestion tracking"})
    issue_id = issue_res.json()["id"]

    client.patch(f"/issues/{issue_id}", json={"status": IssueStatus.VERIFIED.value})

    # Student applies
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    client.post(f"/issues/{issue_id}/applications", json={"proposal": "OpenCV vision model"})

    # Reporter calls POST /issues/{issue_id}/assign
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=reporter_id)
    assign_res = client.post(f"/issues/{issue_id}/assign", json={"student_id": student_id})
    assert assign_res.status_code == status.HTTP_200_OK

    # Verify student points: 50 + 10 = 60
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    stu_pts = client.get("/points/me").json()
    assert stu_pts["points"] == 60
    taken_tx = next((t for t in stu_pts["transactions"] if t["reason"] == "ISSUE_TAKEN"), None)
    assert taken_tx is not None
    assert taken_tx["issue_id"] == issue_id


def test_student_assignment_reward_not_duplicated_on_repeat(client):
    """The assignment reward is not duplicated if the assignment/acceptance operation is repeated."""
    reporter_id = _create_profile(client, role="citizen", name="Repeat Reporter")
    student_id = _create_profile(client, role="student", name="Repeat Student")

    # Issue creation and verification
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=reporter_id)
    issue_id = client.post("/issues", json={"title": "Waste Sensor", "description": "Bin monitor"}).json()["id"]
    client.patch(f"/issues/{issue_id}", json={"status": IssueStatus.VERIFIED.value})

    # Student application
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    client.post(f"/issues/{issue_id}/applications", json={"proposal": "Ultrasonic sensor with LoRa"})

    # Reporter assigns student
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=reporter_id)
    assign1 = client.post(f"/issues/{issue_id}/assign", json={"student_id": student_id})
    assert assign1.status_code == status.HTTP_200_OK

    # Check student balance: 60
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    assert client.get("/points/me").json()["points"] == 60

    # Reporter assigns again (repeat operation)
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=reporter_id)
    assign2 = client.post(f"/issues/{issue_id}/assign", json={"student_id": student_id})
    assert assign2.status_code == status.HTTP_200_OK

    # Check student balance remains 60, only 1 ISSUE_TAKEN transaction
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    pts_data = client.get("/points/me").json()
    assert pts_data["points"] == 60
    taken_txs = [t for t in pts_data["transactions"] if t["reason"] == "ISSUE_TAKEN"]
    assert len(taken_txs) == 1
