import io
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.review import Review


def test_import_valid_csv(client: TestClient):
    """Verify importing a valid CSV creates records and returns summary."""
    proj = client.post("/api/v1/projects", json={"name": "CSV Valid Proj"}).json()
    proj_id = proj["id"]

    csv_data = (
        "customer_name,rating,review_text\n"
        "Alice,5,Fantastic product\n"
        "Bob,4,Very satisfied\n"
        ",3,Anonymous review\n"
    )
    files = {"file": ("reviews.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}

    resp = client.post(f"/api/v1/projects/{proj_id}/reviews/import-csv", files=files)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["project_id"] == proj_id
    assert data["total_rows"] == 3
    assert data["imported_records"] == 3
    assert data["rejected_records"] == 0
    assert len(data["errors"]) == 0

    # Verify records persisted
    reviews_resp = client.get(f"/api/v1/projects/{proj_id}/reviews").json()
    assert reviews_resp["total"] == 3


def test_reject_missing_required_header(client: TestClient):
    """Verify CSV missing required 'rating' or 'review_text' header is rejected with 400."""
    proj = client.post("/api/v1/projects", json={"name": "Header Proj"}).json()
    proj_id = proj["id"]

    csv_data = "customer_name,feedback\nAlice,Great!\n"
    files = {"file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}

    resp = client.post(f"/api/v1/projects/{proj_id}/reviews/import-csv", files=files)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Missing required CSV column" in resp.json()["detail"]


def test_reject_invalid_rating(client: TestClient):
    """Verify CSV with invalid rating returns row-level validation error."""
    proj = client.post("/api/v1/projects", json={"name": "Rating CSV Proj"}).json()
    proj_id = proj["id"]

    csv_data = (
        "customer_name,rating,review_text\n"
        "Alice,7,Invalid rating\n"
    )
    files = {"file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}

    resp = client.post(f"/api/v1/projects/{proj_id}/reviews/import-csv", files=files)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    detail = resp.json()["detail"]
    assert detail["rejected_records"] == 1
    assert detail["imported_records"] == 0
    assert len(detail["errors"]) == 1
    assert detail["errors"][0]["row_number"] == 1
    assert "Rating must be an integer between 1 and 5" in detail["errors"][0]["error"]


def test_reject_empty_review_text(client: TestClient):
    """Verify CSV with blank review text returns validation error."""
    proj = client.post("/api/v1/projects", json={"name": "Blank Text Proj"}).json()
    proj_id = proj["id"]

    csv_data = (
        "customer_name,rating,review_text\n"
        "Alice,5,   \n"
    )
    files = {"file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}

    resp = client.post(f"/api/v1/projects/{proj_id}/reviews/import-csv", files=files)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    detail = resp.json()["detail"]
    assert len(detail["errors"]) == 1
    assert detail["errors"][0]["column"] == "review_text"


def test_report_multiple_row_level_validation_errors(client: TestClient):
    """Verify reporting multiple distinct row validation errors."""
    proj = client.post("/api/v1/projects", json={"name": "Multi Error Proj"}).json()
    proj_id = proj["id"]

    csv_data = (
        "customer_name,rating,review_text\n"
        "Alice,5,Good\n"
        "Bob,abc,Bad rating string\n"
        "Charlie,0,Rating too low\n"
        "Diana,4,\n"
    )
    files = {"file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}

    resp = client.post(f"/api/v1/projects/{proj_id}/reviews/import-csv", files=files)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    detail = resp.json()["detail"]
    assert detail["total_rows"] == 4
    assert len(detail["errors"]) == 3
    # Rows 2, 3, 4 should have errors
    error_rows = [e["row_number"] for e in detail["errors"]]
    assert error_rows == [2, 3, 4]


def test_strict_atomic_import_leaves_no_partial_records(client: TestClient):
    """Verify strict atomic policy: even if row 1 is valid, row 2 failure means NO records saved."""
    proj = client.post("/api/v1/projects", json={"name": "Atomic Proj"}).json()
    proj_id = proj["id"]

    csv_data = (
        "customer_name,rating,review_text\n"
        "Alice,5,Valid review\n"
        "Bob,99,Invalid rating\n"
    )
    files = {"file": ("test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}

    resp = client.post(f"/api/v1/projects/{proj_id}/reviews/import-csv", files=files)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # Check reviews in DB - must be strictly 0
    reviews = client.get(f"/api/v1/projects/{proj_id}/reviews").json()
    assert reviews["total"] == 0
    assert len(reviews["items"]) == 0


def test_handle_empty_file(client: TestClient):
    """Verify empty file upload returns 400."""
    proj = client.post("/api/v1/projects", json={"name": "Empty File Proj"}).json()
    proj_id = proj["id"]

    files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    resp = client.post(f"/api/v1/projects/{proj_id}/reviews/import-csv", files=files)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "empty" in resp.json()["detail"].lower()


def test_handle_invalid_encodings(client: TestClient):
    """Verify uploading non-UTF-8 bytes returns clear client error."""
    proj = client.post("/api/v1/projects", json={"name": "Encoding Proj"}).json()
    proj_id = proj["id"]

    invalid_utf8_bytes = b"\xff\xfe\x00\x00rating,review_text"
    files = {"file": ("invalid.csv", io.BytesIO(invalid_utf8_bytes), "text/csv")}

    resp = client.post(f"/api/v1/projects/{proj_id}/reviews/import-csv", files=files)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "encoding" in resp.json()["detail"].lower()


def test_reject_oversized_file(client: TestClient, monkeypatch):
    """Verify file exceeding MAX_UPLOAD_SIZE_MB is rejected with 413."""
    from app.core import config
    monkeypatch.setattr(config.settings, "MAX_UPLOAD_SIZE_MB", 0)  # max size 0 bytes

    proj = client.post("/api/v1/projects", json={"name": "Oversized Proj"}).json()
    proj_id = proj["id"]

    files = {"file": ("big.csv", io.BytesIO(b"rating,review_text\n5,text\n"), "text/csv")}
    resp = client.post(f"/api/v1/projects/{proj_id}/reviews/import-csv", files=files)
    assert resp.status_code == status.HTTP_413_CONTENT_TOO_LARGE


def test_import_csv_sample_file(client: TestClient):
    """Verify uploading the actual repository sample_reviews.csv succeeds."""
    proj = client.post("/api/v1/projects", json={"name": "Sample CSV Test"}).json()
    proj_id = proj["id"]

    with open("sample_data/sample_reviews.csv", "rb") as f:
        files = {"file": ("sample_reviews.csv", f, "text/csv")}
        resp = client.post(f"/api/v1/projects/{proj_id}/reviews/import-csv", files=files)

    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total_rows"] == 10
    assert data["imported_records"] == 10
    assert data["rejected_records"] == 0
