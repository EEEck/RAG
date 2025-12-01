import pytest
from unittest.mock import MagicMock, patch, ANY
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_ingestion_service():
    with patch("app.routes.ingest.get_ingestion_service") as mock_get:
        mock_service = MagicMock()
        mock_get.return_value = mock_service
        yield mock_service

def test_ingest_file_success(mock_ingestion_service):
    """
    Test that uploading a file and user_id triggers the ingestion service.
    """
    # Mock input data
    file_content = b"fake pdf content"
    filename = "test_upload.pdf"
    user_id = "user_123"

    # Execute request
    response = client.post(
        "/ingest",
        files={"file": (filename, file_content, "application/pdf")},
        data={"user_id": user_id}
    )

    # Verify Response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "book_id" in data

    # Verify Service Call
    # The service should have been called with a temp path (string), a book UUID, and the user_id
    mock_ingestion_service.ingest_book.assert_called_once()

    call_args = mock_ingestion_service.ingest_book.call_args
    assert call_args is not None
    kwargs = call_args.kwargs

    # Check arguments
    assert "file_path" in kwargs
    assert kwargs["file_path"].endswith(".pdf") # Temp file should preserve suffix
    assert "book_id" in kwargs
    assert kwargs["owner_id"] == user_id

def test_ingest_file_missing_user_id():
    """
    Test validation for missing user_id.
    """
    file_content = b"fake content"
    response = client.post(
        "/ingest",
        files={"file": ("test.pdf", file_content, "application/pdf")}
        # Missing data={"user_id": ...}
    )
    assert response.status_code == 422 # Validation error

def test_ingest_service_failure(mock_ingestion_service):
    """
    Test that service exceptions result in a 500 error.
    """
    mock_ingestion_service.ingest_book.side_effect = Exception("Parsing failed")

    response = client.post(
        "/ingest",
        files={"file": ("broken.pdf", b"data", "application/pdf")},
        data={"user_id": "u1"}
    )

    assert response.status_code == 500
    assert "Ingestion failed" in response.json()["detail"]
