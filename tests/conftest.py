import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.database import Base, get_db
from app.main import app


class MockUser:
    def __init__(self, user_id: str, email: str = "test@example.com"):
        self.id = user_id
        self.email = email


@pytest.fixture(name="db_session")
def fixture_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


class MockClassifier:
    """Mock ML classifier for deterministic unit testing without external service."""

    def classify(self, image_path_or_url: str):
        url_lower = str(image_path_or_url).lower()
        if any(k in url_lower for k in ["road", "pothole", "asphalt", "traffic"]):
            category = "Roads & Potholes"
            confidence = 0.94
        elif any(k in url_lower for k in ["garbage", "waste", "trash", "dump"]):
            category = "Garbage & Waste Management"
            confidence = 0.92
        elif any(k in url_lower for k in ["water", "leak", "drain", "flood"]):
            category = "Water Supply & Drainage"
            confidence = 0.91
        elif any(k in url_lower for k in ["light", "electric", "pole", "wire", "streetlight"]):
            category = "Electricity & Street Lighting"
            confidence = 0.89
        else:
            category = "Public Infrastructure"
            confidence = 0.85
        return {
            "category": category,
            "confidence": confidence,
            "priority": "MEDIUM",
            "bbox": None,
        }


@pytest.fixture(autouse=True)
def mock_ml_classifier(monkeypatch):
    mock_instance = MockClassifier()
    monkeypatch.setattr("app.services.ml_classifier.get_issue_classifier", lambda: mock_instance)
    monkeypatch.setattr("app.services.issue.get_issue_classifier", lambda: mock_instance)
    return mock_instance


@pytest.fixture(name="client")
def fixture_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

