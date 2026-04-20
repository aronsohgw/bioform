"""Tests for image upload endpoint."""
import io
from unittest.mock import patch, AsyncMock


MOCK_CLASSIFICATION = {
    "category": "cellular",
    "confidence": 0.85,
    "rationale": "Test classification",
    "architectural_suggestions": ["test suggestion"],
}


async def _mock_classify(*args, **kwargs):
    """Return mock classification result."""
    return MOCK_CLASSIFICATION


def test_upload_returns_200(client, sample_image_bytes):
    with patch("app.main.classify_image", side_effect=_mock_classify):
        response = client.post(
            "/api/upload",
            files={"file": ("test.png", io.BytesIO(sample_image_bytes), "image/png")},
        )
    assert response.status_code == 200


def test_upload_returns_analysis_result(client, sample_image_bytes):
    with patch("app.main.classify_image", side_effect=_mock_classify):
        response = client.post(
            "/api/upload",
            files={"file": ("test.png", io.BytesIO(sample_image_bytes), "image/png")},
        )
    data = response.json()
    assert "category" in data
    assert "extraction_data" in data
    assert "image_dimensions" in data
    assert data["category"] == "cellular"


def test_upload_rejects_non_image(client):
    response = client.post(
        "/api/upload",
        files={"file": ("test.txt", io.BytesIO(b"not an image"), "text/plain")},
    )
    assert response.status_code == 400


def test_upload_rejects_missing_file(client):
    response = client.post("/api/upload")
    assert response.status_code == 422


def test_upload_accepts_jpeg(client, sample_image_bytes):
    with patch("app.main.classify_image", side_effect=_mock_classify):
        response = client.post(
            "/api/upload",
            files={"file": ("test.jpg", io.BytesIO(sample_image_bytes), "image/jpeg")},
        )
    assert response.status_code == 200
