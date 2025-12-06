import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.main import app
from app.routes.profiles import get_profile_service
from app.schemas import TeacherProfile

client = TestClient(app)

def test_get_profile_found():
    mock_service = MagicMock()
    app.dependency_overrides[get_profile_service] = lambda: mock_service

    mock_profile = TeacherProfile(id="p1", user_id="u1", name="T1")
    mock_service.get_profile.return_value = mock_profile

    try:
        resp = client.get("/profiles/p1")
        assert resp.status_code == 200
        assert resp.json()["name"] == "T1"
    finally:
        app.dependency_overrides = {}

def test_get_profile_not_found():
    mock_service = MagicMock()
    app.dependency_overrides[get_profile_service] = lambda: mock_service

    mock_service.get_profile.return_value = None

    try:
        resp = client.get("/profiles/p99")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides = {}

def test_create_profile():
    mock_service = MagicMock()
    app.dependency_overrides[get_profile_service] = lambda: mock_service

    mock_service.create_profile.return_value = TeacherProfile(id="p1", user_id="u1", name="T1")

    try:
        resp = client.post("/profiles", json={"user_id": "u1", "name": "T1"})
        assert resp.status_code == 200
        assert resp.json()["id"] == "p1"
    finally:
        app.dependency_overrides = {}
