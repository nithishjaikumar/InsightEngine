from fastapi import status
from fastapi.testclient import TestClient


def test_create_review_success(client: TestClient):
    """Verify creating a review under an existing project."""
    proj = client.post("/api/v1/projects", json={"name": "App Mobile"}).json()
    proj_id = proj["id"]

    resp = client.post(
        f"/api/v1/projects/{proj_id}/reviews",
        json={
            "customer_name": "Jane Doe",
            "rating": 5,
            "review_text": "Smooth checkout and great performance!",
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["project_id"] == proj_id
    assert data["customer_name"] == "Jane Doe"
    assert data["rating"] == 5
    assert data["review_text"] == "Smooth checkout and great performance!"
    assert "id" in data
    assert "created_at" in data


def test_create_review_unknown_project_returns_404(client: TestClient):
    """Verify creating a review under non-existent project returns 404."""
    resp = client.post(
        "/api/v1/projects/8888/reviews",
        json={"rating": 4, "review_text": "Good"},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_reject_invalid_ratings(client: TestClient):
    """Verify ratings below 1 and above 5 are rejected with 422."""
    proj = client.post("/api/v1/projects", json={"name": "Rating Test"}).json()
    proj_id = proj["id"]

    # Rating below 1
    resp_low = client.post(
        f"/api/v1/projects/{proj_id}/reviews",
        json={"rating": 0, "review_text": "Zero rating"},
    )
    assert resp_low.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Rating above 5
    resp_high = client.post(
        f"/api/v1/projects/{proj_id}/reviews",
        json={"rating": 6, "review_text": "Six rating"},
    )
    assert resp_high.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_reject_empty_review_text(client: TestClient):
    """Verify empty or whitespace-only review text is rejected with 422."""
    proj = client.post("/api/v1/projects", json={"name": "Text Test"}).json()
    proj_id = proj["id"]

    resp1 = client.post(
        f"/api/v1/projects/{proj_id}/reviews",
        json={"rating": 4, "review_text": ""},
    )
    assert resp1.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    resp2 = client.post(
        f"/api/v1/projects/{proj_id}/reviews",
        json={"rating": 4, "review_text": "     "},
    )
    assert resp2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_review_by_id(client: TestClient):
    """Verify retrieving an individual review by ID."""
    proj = client.post("/api/v1/projects", json={"name": "Lookup Proj"}).json()
    rev = client.post(
        f"/api/v1/projects/{proj['id']}/reviews",
        json={"rating": 4, "review_text": "Solid experience"},
    ).json()

    resp = client.get(f"/api/v1/reviews/{rev['id']}")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["id"] == rev["id"]
    assert resp.json()["rating"] == 4


def test_get_review_not_found(client: TestClient):
    """Verify requesting an unknown review ID returns 404."""
    resp = client.get("/api/v1/reviews/99999")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_update_review(client: TestClient):
    """Verify partial review updates for rating, review text, and customer name."""
    proj = client.post("/api/v1/projects", json={"name": "Update Proj"}).json()
    rev = client.post(
        f"/api/v1/projects/{proj['id']}/reviews",
        json={"customer_name": "Old Name", "rating": 3, "review_text": "Okay"},
    ).json()

    resp = client.patch(
        f"/api/v1/reviews/{rev['id']}",
        json={"rating": 5, "review_text": "Updated to excellent!", "customer_name": "New Name"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["rating"] == 5
    assert data["review_text"] == "Updated to excellent!"
    assert data["customer_name"] == "New Name"


def test_delete_review(client: TestClient):
    """Verify deleting a review returns 204 and removes the entity."""
    proj = client.post("/api/v1/projects", json={"name": "Delete Proj"}).json()
    rev = client.post(
        f"/api/v1/projects/{proj['id']}/reviews",
        json={"rating": 2, "review_text": "Will delete"},
    ).json()

    del_resp = client.delete(f"/api/v1/reviews/{rev['id']}")
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT

    get_resp = client.get(f"/api/v1/reviews/{rev['id']}")
    assert get_resp.status_code == status.HTTP_404_NOT_FOUND


def test_review_pagination_and_filtering(client: TestClient):
    """Verify filtering across reviews by rating, project_id, text search, and pagination."""
    proj1 = client.post("/api/v1/projects", json={"name": "Filter Proj 1"}).json()["id"]
    proj2 = client.post("/api/v1/projects", json={"name": "Filter Proj 2"}).json()["id"]

    client.post(f"/api/v1/projects/{proj1}/reviews", json={"rating": 5, "review_text": "Super fast delivery"})
    client.post(f"/api/v1/projects/{proj1}/reviews", json={"rating": 2, "review_text": "Slow delivery"})
    client.post(f"/api/v1/projects/{proj2}/reviews", json={"rating": 5, "review_text": "Loved the app interface"})

    # Filter by project_id
    r_proj1 = client.get(f"/api/v1/reviews?project_id={proj1}").json()
    assert r_proj1["total"] == 2

    # Filter by rating
    r_rating5 = client.get("/api/v1/reviews?rating=5").json()
    assert r_rating5["total"] == 2

    # Filter by search keyword
    r_search = client.get("/api/v1/reviews?search=interface").json()
    assert r_search["total"] == 1
    assert r_search["items"][0]["project_id"] == proj2

    # Pagination
    r_page = client.get("/api/v1/reviews?limit=1&offset=0").json()
    assert len(r_page["items"]) == 1
    assert r_page["total"] == 3
