from fastapi import status
from fastapi.testclient import TestClient


def test_create_project_success(client: TestClient):
    """Verify creating a project succeeds with 201 and returns id and timestamps."""
    response = client.post(
        "/api/v1/projects",
        json={"name": "Grocery Delivery", "description": "Customer feedback for grocery"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Grocery Delivery"
    assert data["description"] == "Customer feedback for grocery"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_project_rejects_duplicate_name(client: TestClient):
    """Verify duplicate project names are rejected with HTTP 409."""
    # Create first
    resp1 = client.post("/api/v1/projects", json={"name": "Payment Gateway"})
    assert resp1.status_code == status.HTTP_201_CREATED

    # Attempt second with identical name
    resp2 = client.post("/api/v1/projects", json={"name": "Payment Gateway"})
    assert resp2.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in resp2.json()["detail"]


def test_create_project_rejects_empty_name(client: TestClient):
    """Verify empty or whitespace-only names are rejected with 422."""
    resp1 = client.post("/api/v1/projects", json={"name": ""})
    assert resp1.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    resp2 = client.post("/api/v1/projects", json={"name": "   "})
    assert resp2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_all_projects_pagination(client: TestClient):
    """Verify listing projects returns pagination metadata and items."""
    for i in range(5):
        client.post("/api/v1/projects", json={"name": f"Project {i}"})

    response = client.get("/api/v1/projects?limit=2&offset=1")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 5
    assert data["limit"] == 2
    assert data["offset"] == 1
    assert len(data["items"]) == 2


def test_get_project_by_id(client: TestClient):
    """Verify retrieving an individual project by ID."""
    created = client.post("/api/v1/projects", json={"name": "Alpha"}).json()
    project_id = created["id"]

    response = client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == project_id
    assert response.json()["name"] == "Alpha"


def test_get_project_not_found(client: TestClient):
    """Verify unknown project ID returns 404."""
    response = client.get("/api/v1/projects/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"]


def test_update_project(client: TestClient):
    """Verify partial updates to project name and description."""
    created = client.post("/api/v1/projects", json={"name": "Original Name"}).json()
    project_id = created["id"]

    # Partial update: change name only
    resp = client.patch(f"/api/v1/projects/{project_id}", json={"name": "Updated Name"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["name"] == "Updated Name"

    # Partial update: change description only
    resp2 = client.patch(f"/api/v1/projects/{project_id}", json={"description": "New description"})
    assert resp2.status_code == status.HTTP_200_OK
    assert resp2.json()["description"] == "New description"
    assert resp2.json()["name"] == "Updated Name"


def test_update_project_duplicate_name_conflict(client: TestClient):
    """Verify updating a project to a name already used by another project returns 409."""
    client.post("/api/v1/projects", json={"name": "Project A"})
    proj_b = client.post("/api/v1/projects", json={"name": "Project B"}).json()

    resp = client.patch(f"/api/v1/projects/{proj_b['id']}", json={"name": "Project A"})
    assert resp.status_code == status.HTTP_409_CONFLICT


def test_delete_project_without_reviews(client: TestClient):
    """Verify deleting a project with 0 reviews returns 204."""
    created = client.post("/api/v1/projects", json={"name": "Disposable Project"}).json()
    project_id = created["id"]

    del_resp = client.delete(f"/api/v1/projects/{project_id}")
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT

    # Verify project is gone
    get_resp = client.get(f"/api/v1/projects/{project_id}")
    assert get_resp.status_code == status.HTTP_404_NOT_FOUND


def test_prevent_deletion_when_reviews_exist(client: TestClient):
    """Verify restrictive deletion policy: deleting project with reviews returns 409."""
    proj = client.post("/api/v1/projects", json={"name": "Active Service"}).json()
    proj_id = proj["id"]

    # Add a review
    rev_resp = client.post(
        f"/api/v1/projects/{proj_id}/reviews",
        json={"rating": 5, "review_text": "Great service!"},
    )
    assert rev_resp.status_code == status.HTTP_201_CREATED

    # Attempt deletion
    del_resp = client.delete(f"/api/v1/projects/{proj_id}")
    assert del_resp.status_code == status.HTTP_409_CONFLICT
    assert "restricted" in del_resp.json()["detail"].lower()

    # Verify project still exists
    get_resp = client.get(f"/api/v1/projects/{proj_id}")
    assert get_resp.status_code == status.HTTP_200_OK


def test_project_analytics_summary(client: TestClient):
    """Verify analytics calculation for empty and populated projects."""
    proj = client.post("/api/v1/projects", json={"name": "Analytics Proj"}).json()
    proj_id = proj["id"]

    # Initially empty
    summary = client.get(f"/api/v1/projects/{proj_id}/analytics/summary").json()
    assert summary["total_reviews"] == 0
    assert summary["average_rating"] is None
    assert summary["rating_counts"] == {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}

    # Add reviews
    client.post(f"/api/v1/projects/{proj_id}/reviews", json={"rating": 5, "review_text": "Top"})
    client.post(f"/api/v1/projects/{proj_id}/reviews", json={"rating": 3, "review_text": "Okay"})

    summary2 = client.get(f"/api/v1/projects/{proj_id}/analytics/summary").json()
    assert summary2["total_reviews"] == 2
    assert summary2["average_rating"] == 4.0
    assert summary2["rating_counts"]["5"] == 1
    assert summary2["rating_counts"]["3"] == 1
