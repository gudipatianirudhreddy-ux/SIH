import uuid
from fastapi import status

from app.auth import get_current_user
from app.main import app
from app.models.enums import (
    ApplicationStatus,
    EvidenceType,
    IssueStatus,
    SponsorshipStatus,
)
from app.models.profile import Profile
from tests.conftest import MockUser


def create_user(client, db_session, role: str, name: str = "Test User") -> str:
    """Helper to create a user profile with role in database."""
    user_id = str(uuid.uuid4())
    user_uuid = uuid.UUID(user_id)
    profile = Profile(id=user_uuid, name=name, role=role)
    db_session.add(profile)
    db_session.commit()
    return user_id


# ==============================================================================
# 1. STUDENT APPLICATION WORKFLOW TESTS
# ==============================================================================
def test_student_application_workflow(client, db_session):
    citizen_id = create_user(client, db_session, role="citizen", name="Reporter Citizen")
    student1_id = create_user(client, db_session, role="student", name="Student One")
    student2_id = create_user(client, db_session, role="student", name="Student Two")

    # 1. Citizen creates issue
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    issue_res = client.post(
        "/issues",
        json={"title": "Solar Water Purifier", "description": "Need clean water solution in village"},
    )
    assert issue_res.status_code == status.HTTP_201_CREATED
    issue_id = issue_res.json()["id"]

    # 2. Student cannot apply if issue is not VERIFIED yet (currently REPORTED)
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student1_id)
    early_apply = client.post(
        f"/issues/{issue_id}/applications",
        json={"proposal": "I have a design for solar distillation"},
    )
    assert early_apply.status_code == status.HTTP_400_BAD_REQUEST

    # 3. Citizen verifies the issue: REPORTED -> VERIFIED
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    verify_res = client.patch(
        f"/issues/{issue_id}",
        json={"status": IssueStatus.VERIFIED.value},
    )
    assert verify_res.status_code == status.HTTP_200_OK
    assert verify_res.json()["status"] == IssueStatus.VERIFIED.value

    # 4. Citizen cannot submit a student application
    citizen_apply = client.post(
        f"/issues/{issue_id}/applications",
        json={"proposal": "Citizen trying to apply as student"},
    )
    assert citizen_apply.status_code == status.HTTP_403_FORBIDDEN

    # 5. Student 1 applies with proposal
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student1_id)
    app1_res = client.post(
        f"/issues/{issue_id}/applications",
        json={"proposal": "I have an optimized multistage solar membrane design"},
    )
    assert app1_res.status_code == status.HTTP_201_CREATED
    app1_data = app1_res.json()
    assert app1_data["student_id"] == student1_id
    assert app1_data["status"] == ApplicationStatus.PENDING.value
    app1_id = app1_data["id"]

    # 6. Student 1 cannot apply twice (duplicate rejection with 409 Conflict)
    dup_res = client.post(
        f"/issues/{issue_id}/applications",
        json={"proposal": "Duplicate application attempt"},
    )
    assert dup_res.status_code == status.HTTP_409_CONFLICT

    # 7. Student 2 also applies with proposal
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student2_id)
    app2_res = client.post(
        f"/issues/{issue_id}/applications",
        json={"proposal": "I propose reverse osmosis with solar battery storage"},
    )
    assert app2_res.status_code == status.HTTP_201_CREATED
    app2_id = app2_res.json()["id"]

    # 8. Student 1 checks /applications/me
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student1_id)
    my_apps = client.get("/applications/me")
    assert my_apps.status_code == status.HTTP_200_OK
    assert len(my_apps.json()) == 1
    assert my_apps.json()[0]["id"] == app1_id

    # 9. Student 1 attempts to accept their own application -> 403 Forbidden
    self_accept = client.patch(
        f"/applications/{app1_id}",
        json={"status": ApplicationStatus.ACCEPTED.value},
    )
    assert self_accept.status_code == status.HTTP_403_FORBIDDEN

    # 10. Issue reporter views all applicants for their issue
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    list_apps = client.get(f"/issues/{issue_id}/applications")
    assert list_apps.status_code == status.HTTP_200_OK
    assert len(list_apps.json()) == 2

    # 11. Issue reporter accepts Student 1's application
    accept_res = client.patch(
        f"/applications/{app1_id}",
        json={"status": ApplicationStatus.ACCEPTED.value},
    )
    assert accept_res.status_code == status.HTTP_200_OK
    assert accept_res.json()["status"] == ApplicationStatus.ACCEPTED.value

    # Verify side effects:
    # a) Student 1 is assigned to the issue
    # b) Issue status transitioned to IN_PROGRESS
    # c) Competing pending application from Student 2 was auto-rejected
    issue_check = client.get(f"/issues/{issue_id}").json()
    assert issue_check["assigned_student_id"] == student1_id
    assert issue_check["status"] == IssueStatus.IN_PROGRESS.value

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student2_id)
    app2_check = client.get("/applications/me").json()
    assert app2_check[0]["status"] == ApplicationStatus.REJECTED.value


def test_student_can_withdraw_application(client, db_session):
    citizen_id = create_user(client, db_session, role="citizen")
    student_id = create_user(client, db_session, role="student")

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    issue_res = client.post("/issues", json={"title": "Road Issue", "description": "Needs road repair"})
    issue_id = issue_res.json()["id"]
    client.patch(f"/issues/{issue_id}", json={"status": IssueStatus.VERIFIED.value})

    # Student applies
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    app_res = client.post(
        f"/issues/{issue_id}/applications",
        json={"proposal": "Road patching with polymer concrete"},
    )
    app_id = app_res.json()["id"]

    # Student withdraws application
    withdraw_res = client.patch(
        f"/applications/{app_id}",
        json={"status": ApplicationStatus.WITHDRAWN.value},
    )
    assert withdraw_res.status_code == status.HTTP_200_OK
    assert withdraw_res.json()["status"] == ApplicationStatus.WITHDRAWN.value


# ==============================================================================
# 2. STUDENT ASSIGNMENT & CONVENIENCE ENDPOINTS
# ==============================================================================
def test_explicit_student_assignment(client, db_session):
    citizen_id = create_user(client, db_session, role="citizen")
    student_id = create_user(client, db_session, role="student", name="Assigned Dev")

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    issue_res = client.post("/issues", json={"title": "Bridge Sensor", "description": "Structural vibration"})
    issue_id = issue_res.json()["id"]
    client.patch(f"/issues/{issue_id}", json={"status": IssueStatus.VERIFIED.value})

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    client.post(f"/issues/{issue_id}/applications", json={"proposal": "Piezoelectric accelerometer array"})

    # Assign via POST /issues/{issue_id}/assign
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    assign_res = client.post(f"/issues/{issue_id}/assign", json={"student_id": student_id})
    assert assign_res.status_code == status.HTTP_200_OK
    assert assign_res.json()["assigned_student_id"] == student_id
    assert assign_res.json()["status"] == IssueStatus.IN_PROGRESS.value

    # Assigned student checks /issues/me/assigned
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    assigned_res = client.get("/issues/me/assigned")
    assert assigned_res.status_code == status.HTTP_200_OK
    assert assigned_res.json()["total"] == 1
    assert assigned_res.json()["items"][0]["id"] == issue_id

    # Citizen checks /issues/me/reported
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    reported_res = client.get("/issues/me/reported")
    assert reported_res.status_code == status.HTTP_200_OK
    assert reported_res.json()["total"] == 1
    assert reported_res.json()["items"][0]["id"] == issue_id


# ==============================================================================
# 3. ISSUE STATUS WORKFLOW & RBAC RESTRICTIONS
# ==============================================================================
def test_status_transitions_and_rejections(client, db_session):
    citizen_id = create_user(client, db_session, role="citizen")
    student_id = create_user(client, db_session, role="student")
    other_citizen_id = create_user(client, db_session, role="citizen")

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    issue_res = client.post("/issues", json={"title": "Smart Grid Failure", "description": "Substation outage"})
    issue_id = issue_res.json()["id"]
    assert issue_res.json()["status"] == IssueStatus.REPORTED.value

    # Invalid jump: REPORTED -> RESOLVED directly (bypass prevention) -> 400 Bad Request
    invalid_jump = client.patch(f"/issues/{issue_id}", json={"status": IssueStatus.RESOLVED.value})
    assert invalid_jump.status_code == status.HTTP_400_BAD_REQUEST

    # Invalid jump: REPORTED -> IN_PROGRESS directly -> 400 Bad Request
    invalid_jump2 = client.patch(f"/issues/{issue_id}", json={"status": IssueStatus.IN_PROGRESS.value})
    assert invalid_jump2.status_code == status.HTTP_400_BAD_REQUEST

    # Valid: REPORTED -> VERIFIED by reporter
    ok_verify = client.patch(f"/issues/{issue_id}", json={"status": IssueStatus.VERIFIED.value})
    assert ok_verify.status_code == status.HTTP_200_OK
    assert ok_verify.json()["status"] == IssueStatus.VERIFIED.value

    # Unauthorized user tries to update issue -> 403 Forbidden
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=other_citizen_id)
    unauth_patch = client.patch(f"/issues/{issue_id}", json={"status": IssueStatus.IN_PROGRESS.value})
    assert unauth_patch.status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# 4. PROGRESS / EVIDENCE TRACKING
# ==============================================================================
def test_progress_evidence_lifecycle(client, db_session):
    citizen_id = create_user(client, db_session, role="citizen")
    student1_id = create_user(client, db_session, role="student", name="Assigned Student")
    student2_id = create_user(client, db_session, role="student", name="Random Student")
    industry_id = create_user(client, db_session, role="industry", name="Tech Mentor")

    # Issue setup & assignment
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    issue_res = client.post("/issues", json={"title": "Water Sensor", "description": "Need TDS and pH sensor"})
    issue_id = issue_res.json()["id"]
    client.patch(f"/issues/{issue_id}", json={"status": IssueStatus.VERIFIED.value})

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student1_id)
    app_res = client.post(f"/issues/{issue_id}/applications", json={"proposal": "Arduino + analog pH probe"})
    app_id = app_res.json()["id"]

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    client.patch(f"/applications/{app_id}", json={"status": ApplicationStatus.ACCEPTED.value})

    # Unassigned student attempts to upload evidence -> 403 Forbidden
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student2_id)
    bad_evidence = client.post(
        f"/issues/{issue_id}/evidence",
        json={"media_url": "https://storage.sih.org/fake.jpg", "description": "Unauthorized"},
    )
    assert bad_evidence.status_code == status.HTTP_403_FORBIDDEN

    # Assigned student uploads progress evidence -> 201 Created
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student1_id)
    ev_res = client.post(
        f"/issues/{issue_id}/evidence",
        json={
            "media_url": "https://storage.sih.org/milestone1_circuit.jpg",
            "description": "Breadboard prototype reading pH 7.2 accurately",
            "evidence_type": EvidenceType.PROGRESS.value,
        },
    )
    assert ev_res.status_code == status.HTTP_201_CREATED
    ev_data = ev_res.json()
    assert ev_data["student_id"] == student1_id
    assert ev_data["evidence_type"] == EvidenceType.PROGRESS.value
    evidence_id = ev_data["id"]

    # View evidence list (Authorized: assigned student, reporter, industry)
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=industry_id)
    ind_view = client.get(f"/issues/{issue_id}/evidence")
    assert ind_view.status_code == status.HTTP_200_OK
    assert len(ind_view.json()) == 1

    # Unauthorized citizen tries to view evidence -> 403 Forbidden
    random_user_id = create_user(client, db_session, role="citizen")
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=random_user_id)
    unauth_view = client.get(f"/issues/{issue_id}/evidence")
    assert unauth_view.status_code == status.HTTP_403_FORBIDDEN

    # Unauthorized user tries to delete evidence -> 403 Forbidden
    unauth_del = client.delete(f"/evidence/{evidence_id}")
    assert unauth_del.status_code == status.HTTP_403_FORBIDDEN

    # Author student deletes evidence -> 204 No Content
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student1_id)
    auth_del = client.delete(f"/evidence/{evidence_id}")
    assert auth_del.status_code == status.HTTP_204_NO_CONTENT


# ==============================================================================
# 5. SOLUTION WORKFLOW & ASSIGNED STUDENT INTEGRATION
# ==============================================================================
def test_solution_submission_assignment_guard(client, db_session):
    citizen_id = create_user(client, db_session, role="citizen")
    assigned_student_id = create_user(client, db_session, role="student", name="Assigned Solver")
    random_student_id = create_user(client, db_session, role="student", name="Unassigned Student")
    industry_id = create_user(client, db_session, role="industry", name="Industrial Sponsor")

    # Citizen creates issue and verifies
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    issue_res = client.post("/issues", json={"title": "Solar Inverter", "description": "Need 5kW pure sine wave"})
    issue_id = issue_res.json()["id"]
    client.patch(f"/issues/{issue_id}", json={"status": IssueStatus.VERIFIED.value})

    # Student applies and gets accepted
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=assigned_student_id)
    app_res = client.post(f"/issues/{issue_id}/applications", json={"proposal": "SPWM H-bridge design"})
    app_id = app_res.json()["id"]

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    client.patch(f"/applications/{app_id}", json={"status": ApplicationStatus.ACCEPTED.value})

    # Unassigned student attempts to submit solution -> 403 Forbidden
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=random_student_id)
    bad_sol = client.post(
        f"/issues/{issue_id}/solutions",
        json={"title": "Unassigned Solution", "description": "Attempting solution without assignment"},
    )
    assert bad_sol.status_code == status.HTTP_403_FORBIDDEN

    # Assigned student submits solution -> 201 Created
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=assigned_student_id)
    good_sol = client.post(
        f"/issues/{issue_id}/solutions",
        json={
            "title": "5kW SPWM Solar Inverter Complete",
            "description": "96% efficiency with MPPT tracking and remote telemetry",
            "pdf_url": "https://storage.sih.org/inverter_schematics.pdf",
            "prototype_url": "https://github.com/team/inverter-firmware",
        },
    )
    assert good_sol.status_code == status.HTTP_201_CREATED
    sol_id = good_sol.json()["id"]

    # Issue auto-transitions to SOLUTION_SUBMITTED
    issue_state = client.get(f"/issues/{issue_id}").json()
    assert issue_state["status"] == IssueStatus.SOLUTION_SUBMITTED.value

    # Student checks /issues/me/solutions
    my_sols = client.get("/issues/me/solutions")
    assert my_sols.status_code == status.HTTP_200_OK
    assert len(my_sols.json()) == 1
    assert my_sols.json()[0]["id"] == sol_id

    # Industry reviews solution -> transitions solution to UNDER_REVIEW and issue to EVALUATED
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=industry_id)
    review_res = client.post(
        f"/solutions/{sol_id}/reviews",
        json={"rating": 5, "feedback": "Superb hardware design and test results."},
    )
    assert review_res.status_code == status.HTTP_201_CREATED

    issue_eval = client.get(f"/issues/{issue_id}").json()
    assert issue_eval["status"] == IssueStatus.EVALUATED.value

    # Issue reporter resolves the evaluated issue: EVALUATED -> RESOLVED
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    resolve_res = client.patch(
        f"/issues/{issue_id}",
        json={"status": IssueStatus.RESOLVED.value},
    )
    assert resolve_res.status_code == status.HTTP_200_OK
    assert resolve_res.json()["status"] == IssueStatus.RESOLVED.value


# ==============================================================================
# 6. INDUSTRY SPONSORSHIP WORKFLOW
# ==============================================================================
def test_industry_sponsorship_workflow(client, db_session):
    citizen_id = create_user(client, db_session, role="citizen")
    student_id = create_user(client, db_session, role="student")
    industry_id = create_user(client, db_session, role="industry", name="Tata Motors CSR")

    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    issue_res = client.post("/issues", json={"title": "EV Charging Station", "description": "Solar EV charging hub"})
    issue_id = issue_res.json()["id"]

    # Student tries to create sponsorship -> 403 Forbidden
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    student_sponsor = client.post(
        f"/issues/{issue_id}/sponsorships",
        json={"amount": 50000.0, "message": "Student pledge"},
    )
    assert student_sponsor.status_code == status.HTTP_403_FORBIDDEN

    # Industry pledges sponsorship with negative amount -> 422 or 400 Bad Request
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=industry_id)
    neg_sponsor = client.post(
        f"/issues/{issue_id}/sponsorships",
        json={"amount": -100.0, "message": "Negative amount test"},
    )
    assert neg_sponsor.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY)

    # Industry creates valid sponsorship
    sponsor_res = client.post(
        f"/issues/{issue_id}/sponsorships",
        json={"amount": 75000.0, "message": "Grant for prototype hardware and battery procurement"},
    )
    assert sponsor_res.status_code == status.HTTP_201_CREATED
    sponsor_data = sponsor_res.json()
    assert sponsor_data["amount"] == 75000.0
    assert sponsor_data["status"] == SponsorshipStatus.PLEDGED.value
    sponsor_id = sponsor_data["id"]

    # View sponsorships list
    list_sponsors = client.get(f"/issues/{issue_id}/sponsorships")
    assert list_sponsors.status_code == status.HTTP_200_OK
    assert len(list_sponsors.json()) == 1

    # Issue reporter approves sponsorship
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    approve_res = client.patch(
        f"/sponsorships/{sponsor_id}",
        json={"status": SponsorshipStatus.APPROVED.value},
    )
    assert approve_res.status_code == status.HTTP_200_OK
    assert approve_res.json()["status"] == SponsorshipStatus.APPROVED.value


# ==============================================================================
# 7. DASHBOARDS FOR ALL ROLES
# ==============================================================================
def test_dashboards(client, db_session):
    citizen_id = create_user(client, db_session, role="citizen")
    student_id = create_user(client, db_session, role="student")
    industry_id = create_user(client, db_session, role="industry")

    # Citizen reports issue
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    issue_res = client.post("/issues", json={"title": "Road Hazard", "description": "Pot hole issue"})
    issue_id = issue_res.json()["id"]
    client.patch(f"/issues/{issue_id}", json={"status": IssueStatus.VERIFIED.value})

    # Student applies
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    app_res = client.post(f"/issues/{issue_id}/applications", json={"proposal": "Repair methodology"})
    app_id = app_res.json()["id"]

    # Reporter accepts student
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    client.patch(f"/applications/{app_id}", json={"status": ApplicationStatus.ACCEPTED.value})

    # Industry sponsors
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=industry_id)
    client.post(f"/issues/{issue_id}/sponsorships", json={"amount": 25000.0})

    # 1. Check Citizen Dashboard
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen_id)
    cit_dash = client.get("/dashboard/citizen")
    assert cit_dash.status_code == status.HTTP_200_OK
    cit_data = cit_dash.json()
    assert cit_data["total_reported"] == 1
    assert cit_data["in_progress_issues"] == 1
    assert len(cit_data["recent_reported_issues"]) == 1

    # 2. Check Student Dashboard
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student_id)
    stu_dash = client.get("/dashboard/student")
    assert stu_dash.status_code == status.HTTP_200_OK
    stu_data = stu_dash.json()
    assert stu_data["applications_count"] == 1
    assert stu_data["accepted_applications"] == 1
    assert stu_data["assigned_issues"] == 1

    # 3. Check Industry Dashboard
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=industry_id)
    ind_dash = client.get("/dashboard/industry")
    assert ind_dash.status_code == status.HTTP_200_OK
    ind_data = ind_dash.json()
    assert ind_data["sponsored_issues_count"] == 1
    assert ind_data["total_sponsored_amount"] == 25000.0


# ==============================================================================
# 8. IDOR & CROSS-TENANT ISOLATION TESTS
# ==============================================================================
def test_idor_protections(client, db_session):
    citizen1_id = create_user(client, db_session, role="citizen", name="Citizen 1")
    citizen2_id = create_user(client, db_session, role="citizen", name="Citizen 2")
    student1_id = create_user(client, db_session, role="student", name="Student 1")
    student2_id = create_user(client, db_session, role="student", name="Student 2")
    industry1_id = create_user(client, db_session, role="industry", name="Industry 1")
    industry2_id = create_user(client, db_session, role="industry", name="Industry 2")

    # Citizen 1 creates and verifies issue
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen1_id)
    issue_res = client.post("/issues", json={"title": "Private Issue", "description": "Needs repair"})
    issue_id = issue_res.json()["id"]
    client.patch(f"/issues/{issue_id}", json={"status": IssueStatus.VERIFIED.value})

    # Student 1 applies
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student1_id)
    app1_res = client.post(f"/issues/{issue_id}/applications", json={"proposal": "Student 1 proposal"})
    app1_id = app1_res.json()["id"]

    # Student 2 cannot withdraw Student 1's application (IDOR guard)
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=student2_id)
    bad_withdraw = client.patch(f"/applications/{app1_id}", json={"status": ApplicationStatus.WITHDRAWN.value})
    assert bad_withdraw.status_code == status.HTTP_403_FORBIDDEN

    # Citizen 2 cannot accept Student 1's application on Citizen 1's issue (IDOR guard)
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=citizen2_id)
    bad_accept = client.patch(f"/applications/{app1_id}", json={"status": ApplicationStatus.ACCEPTED.value})
    assert bad_accept.status_code == status.HTTP_403_FORBIDDEN

    # Industry 1 creates sponsorship
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=industry1_id)
    spons_res = client.post(f"/issues/{issue_id}/sponsorships", json={"amount": 10000.0, "message": "Pledge 1"})
    spons_id = spons_res.json()["id"]

    # Industry 2 cannot edit Industry 1's sponsorship amount (IDOR guard)
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=industry2_id)
    bad_edit_spons = client.patch(f"/sponsorships/{spons_id}", json={"amount": 5.0})
    assert bad_edit_spons.status_code == status.HTTP_403_FORBIDDEN

