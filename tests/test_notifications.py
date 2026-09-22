import time
import uuid
import pytest
from fastapi import status

from app.auth import get_current_user
from app.main import app
from app.models.enums import IssueStatus, NotificationType, SolutionStatus
from app.models.interest import IndustrialistInterest, StudentInterest
from tests.conftest import MockUser


def _create_user(client, role: str, name: str) -> str:
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)
    res = client.post("/profiles/me", json={"name": name, "role": role})
    assert res.status_code == status.HTTP_201_CREATED
    return user_id


def _create_verified_issue(client, reporter_id: str, title: str = "Pothole on Main Road") -> str:
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=reporter_id)
    issue_res = client.post(
        "/issues",
        json={"title": title, "description": "Severe road damage", "category": "Roads & Potholes"},
    )
    assert issue_res.status_code == status.HTTP_201_CREATED
    issue_id = issue_res.json()["id"]

    verify_res = client.patch(f"/issues/{issue_id}", json={"status": IssueStatus.VERIFIED.value})
    assert verify_res.status_code == status.HTTP_200_OK
    return issue_id


def test_get_notifications_empty(client):
    user_id = _create_user(client, role="citizen", name="Empty Citizen")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    res = client.get("/notifications/me")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["unread_count"] == 0


def test_issue_submitted_and_verified_creates_notifications(client):
    reporter_id = _create_user(client, role="citizen", name="Road Citizen")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=reporter_id)

    # 1. Submit issue
    issue_res = client.post(
        "/issues",
        json={"title": "Pothole on 5th Ave", "description": "Big hole in road", "category": "Roads & Potholes"},
    )
    assert issue_res.status_code == status.HTTP_201_CREATED
    issue_id = issue_res.json()["id"]

    # Reporter should have 1 unread notification (ISSUE_SUBMITTED)
    res = client.get("/notifications/me")
    assert res.status_code == status.HTTP_200_OK
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["type"] == NotificationType.ISSUE_SUBMITTED.value
    assert items[0]["is_read"] is False
    assert items[0]["related_issue_id"] == issue_id

    time.sleep(0.02)

    # 2. Verify issue
    verify_res = client.patch(f"/issues/{issue_id}", json={"status": IssueStatus.VERIFIED.value})
    assert verify_res.status_code == status.HTTP_200_OK

    # Reporter should now have 2 notifications (ISSUE_VERIFIED newest first)
    res = client.get("/notifications/me")
    items = res.json()["items"]
    assert len(items) == 2
    types = [i["type"] for i in items]
    assert types[0] == NotificationType.ISSUE_VERIFIED.value
    assert types[1] == NotificationType.ISSUE_SUBMITTED.value


def test_notifications_unread_count_and_mark_read(client):
    reporter_id = _create_user(client, role="citizen", name="Counting Citizen")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=reporter_id)

    # Submit issue -> creates 1 notification
    client.post(
        "/issues",
        json={"title": "Streetlight Broken", "description": "Dark area", "category": "Electricity & Street Lighting"},
    )

    count_res = client.get("/notifications/unread-count")
    assert count_res.status_code == status.HTTP_200_OK
    assert count_res.json()["count"] == 1

    list_res = client.get("/notifications/me")
    notif_id = list_res.json()["items"][0]["id"]

    # Mark single notification as read
    patch_res = client.patch(f"/notifications/{notif_id}/read")
    assert patch_res.status_code == status.HTTP_200_OK
    assert patch_res.json()["is_read"] is True

    # Check unread count is now 0
    count_res = client.get("/notifications/unread-count")
    assert count_res.json()["count"] == 0

    # Unread-only filter returns empty
    unread_res = client.get("/notifications/me?unread_only=true")
    assert unread_res.json()["items"] == []
    assert unread_res.json()["total"] == 0


def test_mark_all_notifications_as_read(client):
    reporter_id = _create_user(client, role="citizen", name="Multi Notif Citizen")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=reporter_id)

    # Create 2 issues
    client.post("/issues", json={"title": "Issue 1", "description": "Desc 1"})
    client.post("/issues", json={"title": "Issue 2", "description": "Desc 2"})

    count_res = client.get("/notifications/unread-count")
    assert count_res.json()["count"] == 2

    # Mark all as read
    read_all_res = client.patch("/notifications/read-all")
    assert read_all_res.status_code == status.HTTP_200_OK
    assert read_all_res.json()["count"] == 2

    # Unread count is now 0
    count_res = client.get("/notifications/unread-count")
    assert count_res.json()["count"] == 0


def test_user_cannot_read_another_users_notification(client):
    user_a = _create_user(client, role="citizen", name="User A")
    user_b = _create_user(client, role="citizen", name="User B")

    # User A creates issue -> gets notification
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_a)
    client.post("/issues", json={"title": "User A Issue", "description": "Desc A"})
    list_a = client.get("/notifications/me")
    notif_a_id = list_a.json()["items"][0]["id"]

    # User B attempts to mark User A's notification as read -> 403 Forbidden
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_b)
    patch_res = client.patch(f"/notifications/{notif_a_id}/read")
    assert patch_res.status_code == status.HTTP_403_FORBIDDEN


def test_application_flow_notifications(client):
    reporter_id = _create_user(client, role="citizen", name="App Flow Citizen")
    student_id = _create_user(client, role="student", name="App Flow Student")
    issue_id = _create_verified_issue(client, reporter_id, title="Water Leak")

    # Student submits application
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    app_res = client.post(
        f"/issues/{issue_id}/applications",
        json={"proposal": "Smart acoustic leak detector"},
    )
    assert app_res.status_code == status.HTTP_201_CREATED
    application_id = app_res.json()["id"]

    # Reporter should receive APPLICATION_SUBMITTED notification
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=reporter_id)
    rep_notifs = client.get("/notifications/me").json()["items"]
    app_submitted = [n for n in rep_notifs if n["type"] == NotificationType.APPLICATION_SUBMITTED.value]
    assert len(app_submitted) == 1
    assert app_submitted[0]["related_application_id"] == application_id

    # Reporter rejects application
    reject_res = client.patch(f"/applications/{application_id}", json={"status": "REJECTED"})
    assert reject_res.status_code == status.HTTP_200_OK

    # Student should receive APPLICATION_REJECTED notification
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    student_notifs = client.get("/notifications/me").json()["items"]
    app_rejected = [n for n in student_notifs if n["type"] == NotificationType.APPLICATION_REJECTED.value]
    assert len(app_rejected) == 1
    assert app_rejected[0]["related_application_id"] == application_id


def test_application_selected_and_collaboration_flow_notifications(client):
    reporter_id = _create_user(client, role="citizen", name="Collab Citizen")
    student1_id = _create_user(client, role="student", name="Selected Student")
    student2_id = _create_user(client, role="student", name="Other Student")
    industrialist_id = _create_user(client, role="industrialist", name="Selecting Industrialist")

    issue_id = _create_verified_issue(client, reporter_id, title="Bridge Monitoring")

    # Student 1 applies
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student1_id)
    app1_res = client.post(
        f"/issues/{issue_id}/applications",
        json={"proposal": "Sensor mesh network"},
    )
    app1_id = app1_res.json()["id"]

    # Student 2 applies
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student2_id)
    app2_res = client.post(
        f"/issues/{issue_id}/applications",
        json={"proposal": "Drone imaging system"},
    )
    app2_id = app2_res.json()["id"]

    # Industrialist selects Student 1
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=industrialist_id)
    select_res = client.post(f"/applications/{app1_id}/select")
    assert select_res.status_code == status.HTTP_201_CREATED
    collaboration_id = select_res.json()["id"]

    # 1. Student 1 should receive APPLICATION_SELECTED and COLLABORATION_STARTED
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student1_id)
    s1_notifs = client.get("/notifications/me").json()["items"]
    types_s1 = [n["type"] for n in s1_notifs]
    assert NotificationType.APPLICATION_SELECTED.value in types_s1
    assert NotificationType.COLLABORATION_STARTED.value in types_s1

    # 2. Industrialist should receive COLLABORATION_STARTED
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=industrialist_id)
    ind_notifs = client.get("/notifications/me").json()["items"]
    types_ind = [n["type"] for n in ind_notifs]
    assert NotificationType.COLLABORATION_STARTED.value in types_ind

    # 3. Student 2 should receive APPLICATION_REJECTED (auto-rejection on another selection)
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student2_id)
    s2_notifs = client.get("/notifications/me").json()["items"]
    types_s2 = [n["type"] for n in s2_notifs]
    assert NotificationType.APPLICATION_REJECTED.value in types_s2

    # 4. Collaboration completed
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=industrialist_id)
    comp_res = client.patch(f"/collaborations/{collaboration_id}/status", json={"status": "COMPLETED"})
    assert comp_res.status_code == status.HTTP_200_OK

    # Both student 1 and industrialist get COLLABORATION_COMPLETED
    s1_notifs = client.get("/notifications/me").json()["items"]
    assert any(n["type"] == NotificationType.COLLABORATION_COMPLETED.value for n in s1_notifs)

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student1_id)
    s1_notifs = client.get("/notifications/me").json()["items"]
    assert any(n["type"] == NotificationType.COLLABORATION_COMPLETED.value for n in s1_notifs)


def test_solution_submission_and_status_notification(client):
    reporter_id = _create_user(client, role="citizen", name="Sol Reporter")
    student_id = _create_user(client, role="student", name="Sol Student")
    industrialist_id = _create_user(client, role="industrialist", name="Sol Industrialist")
    issue_id = _create_verified_issue(client, reporter_id, title="Water Overflow")

    # Student applies for issue first
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    app_res = client.post(
        f"/issues/{issue_id}/applications",
        json={"proposal": "Drainage overhaul proposal"},
    )
    assert app_res.status_code == status.HTTP_201_CREATED

    # Reporter assigns student to issue
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=reporter_id)
    assign_res = client.post(f"/issues/{issue_id}/assign", json={"student_id": student_id})
    assert assign_res.status_code == status.HTTP_200_OK

    # Student submits solution
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    sol_res = client.post(
        f"/issues/{issue_id}/solutions",
        json={"title": "Drainage Sump Pump", "description": "Automated float switch pump"},
    )
    assert sol_res.status_code == status.HTTP_201_CREATED
    sol_id = sol_res.json()["id"]

    # Reporter receives SOLUTION_SUBMITTED notification
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=reporter_id)
    rep_notifs = client.get("/notifications/me").json()["items"]
    assert any(n["type"] == NotificationType.SOLUTION_SUBMITTED.value for n in rep_notifs)

    # Industrialist updates solution status to UNDER_REVIEW
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=industrialist_id)
    patch_res = client.patch(f"/solutions/{sol_id}", json={"status": SolutionStatus.UNDER_REVIEW.value})
    assert patch_res.status_code == status.HTTP_200_OK

    # Student receives SOLUTION_STATUS_CHANGED notification
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    stud_notifs = client.get("/notifications/me").json()["items"]
    assert any(n["type"] == NotificationType.SOLUTION_STATUS_CHANGED.value for n in stud_notifs)


def test_interest_matching_notification(client, db_session):
    industrialist_id = _create_user(client, role="industrialist", name="Green Industrialist")
    student_id = _create_user(client, role="student", name="Interested Student")
    reporter_id = _create_user(client, role="citizen", name="Issue Citizen")

    # 1. Industrialist registers interest
    db_session.add(IndustrialistInterest(
        profile_id=uuid.UUID(industrialist_id),
        company_name="Clean Rivers Inc",
        focus_areas="Water Supply & Drainage, Sanitation",
    ))
    # 2. Student registers interest
    db_session.add(StudentInterest(
        profile_id=uuid.UUID(student_id),
        institution_name="Engineering College",
        interest_areas="Water Supply & Drainage, Hydraulics",
    ))
    db_session.commit()

    # 3. Citizen creates issue matching "Water Supply & Drainage"
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=reporter_id)
    issue_res = client.post(
        "/issues",
        json={"title": "Broken Water Pipe", "description": "Flooding streets", "category": "Water Supply & Drainage"},
    )
    assert issue_res.status_code == status.HTTP_201_CREATED
    issue_id = issue_res.json()["id"]

    # 4. Check industrialist received INTEREST_MATCH notification
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=industrialist_id)
    ind_notifs = client.get("/notifications/me").json()["items"]
    assert any(
        n["type"] == NotificationType.INTEREST_MATCH.value and n["related_issue_id"] == issue_id
        for n in ind_notifs
    )

    # 5. Check student received INTEREST_MATCH notification
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    stud_notifs = client.get("/notifications/me").json()["items"]
    assert any(
        n["type"] == NotificationType.INTEREST_MATCH.value and n["related_issue_id"] == issue_id
        for n in stud_notifs
    )
