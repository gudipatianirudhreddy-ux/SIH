import uuid
import pytest
from fastapi import status

from app.auth import get_current_user
from app.main import app
from app.models.point_transaction import PointTransaction
from app.models.profile import Profile
from app.services.profile import WELCOME_BONUS
from tests.conftest import MockUser


def test_welcome_bonus_on_profile_creation(client, db_session):
    """Creating a new profile initializes user with 50 points and creates WELCOME_BONUS transaction."""
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    payload = {
        "name": "Jane Doe",
        "role": "citizen",
        "phone_number": "+91 9123456780",
    }
    response = client.post("/profiles/me", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["points"] == WELCOME_BONUS
    assert data["points"] == 50

    # Verify directly in DB
    profile = db_session.query(Profile).filter(Profile.id == uuid.UUID(user_id)).first()
    assert profile is not None
    assert profile.points == 50

    # Verify PointTransaction in DB
    txs = db_session.query(PointTransaction).filter(PointTransaction.user_id == uuid.UUID(user_id)).all()
    assert len(txs) == 1
    assert txs[0].points == 50
    assert txs[0].reason == "WELCOME_BONUS"
    assert txs[0].issue_id is None


def test_no_duplicate_welcome_bonus_on_conflict_or_update(client, db_session):
    """Existing profiles cannot be created again and profile updates do not re-award welcome bonus."""
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    # 1. Initial creation
    res1 = client.post("/profiles/me", json={"name": "Alice", "role": "student"})
    assert res1.status_code == status.HTTP_201_CREATED
    assert res1.json()["points"] == 50

    # 2. Attempt duplicate creation -> 409 Conflict
    res2 = client.post("/profiles/me", json={"name": "Alice", "role": "student"})
    assert res2.status_code == status.HTTP_409_CONFLICT

    # 3. Update profile details via PATCH -> points must stay 50, no new transaction
    patch_res = client.patch("/profiles/me", json={"name": "Alice Wonderland"})
    assert patch_res.status_code == status.HTTP_200_OK

    txs = db_session.query(PointTransaction).filter(PointTransaction.user_id == uuid.UUID(user_id)).all()
    assert len(txs) == 1
    profile = db_session.query(Profile).filter(Profile.id == uuid.UUID(user_id)).first()
    assert profile.points == 50


def test_get_points_me_authenticated(client):
    """Authenticated user retrieves their current balance and list of transactions."""
    user_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_id)

    # Create profile
    client.post("/profiles/me", json={"name": "Points Tester", "role": "citizen"})

    # Check GET /points/me
    response = client.get("/points/me")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "points" in data
    assert data["points"] == 50
    assert "transactions" in data
    assert len(data["transactions"]) == 1
    tx = data["transactions"][0]
    assert tx["user_id"] == user_id
    assert tx["points"] == 50
    assert tx["reason"] == "WELCOME_BONUS"
    assert tx["issue_id"] is None
    assert "created_at" in tx


def test_get_points_me_unauthenticated(client):
    """Unauthenticated request to /points/me is rejected."""
    app.dependency_overrides.clear()
    response = client.get("/points/me")
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


def test_points_user_isolation(client):
    """Transactions and balance are tied strictly to authenticated user and cannot expose other users."""
    user_a_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())

    # User A setup
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_a_id)
    client.post("/profiles/me", json={"name": "User Alpha", "role": "citizen"})

    # User B setup
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_b_id)
    client.post("/profiles/me", json={"name": "User Beta", "role": "student"})

    # Check User B's points
    res_b = client.get("/points/me")
    assert res_b.status_code == status.HTTP_200_OK
    b_data = res_b.json()
    assert b_data["points"] == 50
    for tx in b_data["transactions"]:
        assert tx["user_id"] == user_b_id
        assert tx["user_id"] != user_a_id

    # Switch back to User A and check User A's points
    app.dependency_overrides[get_current_user] = lambda: MockUser(user_id=user_a_id)
    res_a = client.get("/points/me")
    assert res_a.status_code == status.HTTP_200_OK
    a_data = res_a.json()
    for tx in a_data["transactions"]:
        assert tx["user_id"] == user_a_id
        assert tx["user_id"] != user_b_id


def test_database_points_rollback_integrity(db_session):
    """Rollback on failed operation does not leave orphan point transactions or corrupted points."""
    user_uuid = uuid.uuid4()
    profile = Profile(id=user_uuid, name="Rollback Tester", role="citizen", points=50)
    db_session.add(profile)
    db_session.commit()

    initial_points = profile.points
    initial_tx_count = db_session.query(PointTransaction).filter(PointTransaction.user_id == user_uuid).count()
    assert initial_tx_count == 0

    # Start a nested transaction / savepoint
    try:
        profile.points += 20
        failed_tx = PointTransaction(user_id=user_uuid, points=20, reason="FAILED_OP")
        db_session.add(failed_tx)
        # Simulate a crash/exception before commit
        raise RuntimeError("Simulated failure in database workflow")
    except RuntimeError:
        db_session.rollback()

    # Re-fetch profile from database session
    db_profile = db_session.query(Profile).filter(Profile.id == user_uuid).first()
    assert db_profile.points == initial_points
    tx_count_after = db_session.query(PointTransaction).filter(PointTransaction.user_id == user_uuid).count()
    assert tx_count_after == 0
