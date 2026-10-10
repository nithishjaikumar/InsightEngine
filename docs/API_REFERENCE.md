# InsightEngine — REST API Reference

Base URL: `http://127.0.0.1:8000`  
API Prefix: `/api/v1`

---

## 1. System Endpoints

### `GET /health`
- **Purpose**: Verify service health and active environment.
- **Success Status**: `200 OK`
- **Response**:
```json
{
  "status": "ok",
  "app": "InsightEngine",
  "environment": "development"
}
```

---

## 2. Project Endpoints

### `POST /api/v1/projects`
- **Purpose**: Create a new feedback project.
- **Success Status**: `201 Created`
- **Possible Errors**: `409 Conflict` (duplicate name), `422 Unprocessable Entity` (empty name)
- **Request Body**:
```json
{
  "name": "Grocery Delivery",
  "description": "Customer feedback for grocery delivery service"
}
```
- **Response Body**:
```json
{
  "id": 1,
  "name": "Grocery Delivery",
  "description": "Customer feedback for grocery delivery service",
  "created_at": "2026-10-10T17:30:00Z",
  "updated_at": "2026-10-10T17:30:00Z"
}
```

---

### `GET /api/v1/projects`
- **Purpose**: Retrieve a paginated list of projects.
- **Query Parameters**:
  - `limit` (integer, default: 20, max: 100)
  - `offset` (integer, default: 0)
- **Success Status**: `200 OK`
- **Response Body**:
```json
{
  "total": 1,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "name": "Grocery Delivery",
      "description": "Customer feedback for grocery delivery service",
      "created_at": "2026-10-10T17:30:00Z",
      "updated_at": "2026-10-10T17:30:00Z"
    }
  ]
}
```

---

### `GET /api/v1/projects/{project_id}`
- **Purpose**: Retrieve a specific project by ID.
- **Success Status**: `200 OK`
- **Possible Errors**: `404 Not Found`
- **Response Body**:
```json
{
  "id": 1,
  "name": "Grocery Delivery",
  "description": "Customer feedback for grocery delivery service",
  "created_at": "2026-10-10T17:30:00Z",
  "updated_at": "2026-10-10T17:30:00Z"
}
```

---

### `PATCH /api/v1/projects/{project_id}`
- **Purpose**: Partially update project name or description.
- **Success Status**: `200 OK`
- **Possible Errors**: `404 Not Found`, `409 Conflict`, `422 Unprocessable Entity`
- **Request Body**:
```json
{
  "description": "Updated project description"
}
```
- **Response Body**:
```json
{
  "id": 1,
  "name": "Grocery Delivery",
  "description": "Updated project description",
  "created_at": "2026-10-10T17:30:00Z",
  "updated_at": "2026-10-10T17:35:00Z"
}
```

---

### `DELETE /api/v1/projects/{project_id}`
- **Purpose**: Delete a project if and only if it has zero associated reviews.
- **Success Status**: `204 No Content`
- **Possible Errors**: `404 Not Found`, `409 Conflict` (if reviews exist)

---

## 3. Review Endpoints

### `POST /api/v1/projects/{project_id}/reviews`
- **Purpose**: Create a review under a specified project.
- **Success Status**: `201 Created`
- **Possible Errors**: `404 Not Found` (unknown project), `422 Unprocessable Entity` (invalid rating or empty review text)
- **Request Body**:
```json
{
  "customer_name": "Alice Smith",
  "rating": 5,
  "review_text": "The delivery was lightning fast and items were fresh!"
}
```
- **Response Body**:
```json
{
  "id": 1,
  "project_id": 1,
  "customer_name": "Alice Smith",
  "rating": 5,
  "review_text": "The delivery was lightning fast and items were fresh!",
  "created_at": "2026-10-10T17:40:00Z",
  "updated_at": "2026-10-10T17:40:00Z"
}
```

---

### `GET /api/v1/projects/{project_id}/reviews`
- **Purpose**: Retrieve paginated reviews belonging to a specific project with optional rating and search filters.
- **Query Parameters**:
  - `limit` (int, default: 20)
  - `offset` (int, default: 0)
  - `rating` (int, 1-5, optional)
  - `search` (string, optional)
- **Success Status**: `200 OK`
- **Possible Errors**: `404 Not Found` (unknown project)

---

### `GET /api/v1/reviews`
- **Purpose**: Retrieve reviews across all projects with filters.
- **Query Parameters**:
  - `project_id` (int, optional)
  - `rating` (int, 1-5, optional)
  - `search` (string, optional)
  - `limit` (int, default: 20)
  - `offset` (int, default: 0)
- **Success Status**: `200 OK`

---

### `GET /api/v1/reviews/{review_id}`
- **Purpose**: Retrieve an individual review.
- **Success Status**: `200 OK`
- **Possible Errors**: `404 Not Found`

---

### `PATCH /api/v1/reviews/{review_id}`
- **Purpose**: Partially update customer name, rating, or review text.
- **Success Status**: `200 OK`
- **Possible Errors**: `404 Not Found`, `422 Unprocessable Entity`
- **Request Body**:
```json
{
  "rating": 4,
  "review_text": "Updated feedback text"
}
```

---

### `DELETE /api/v1/reviews/{review_id}`
- **Purpose**: Delete a customer review.
- **Success Status**: `204 No Content`
- **Possible Errors**: `404 Not Found`

---

## 4. CSV Ingestion & Analytics Endpoints

### `POST /api/v1/projects/{project_id}/reviews/import-csv`
- **Purpose**: Ingest customer feedback reviews in bulk from a multipart CSV file.
- **Content-Type**: `multipart/form-data`
- **Parameters**: `file` (.csv file)
- **Success Status**: `200 OK`
- **Possible Errors**:
  - `400 Bad Request` (missing headers, validation errors, empty file, non-UTF8 encoding)
  - `404 Not Found` (unknown project)
  - `413 Content Too Large` (file exceeds configured size limit)
- **Success Response**:
```json
{
  "project_id": 1,
  "total_rows": 10,
  "imported_records": 10,
  "rejected_records": 0,
  "errors": [],
  "message": "Successfully imported 10 review(s) into project Grocery Delivery."
}
```
- **Error Response (Atomic Rollback)**:
```json
{
  "detail": {
    "project_id": 1,
    "total_rows": 5,
    "imported_records": 0,
    "rejected_records": 5,
    "errors": [
      {
        "row_number": 2,
        "column": "rating",
        "error": "Rating must be an integer between 1 and 5, received '9'"
      }
    ],
    "message": "Import failed: 1 validation error(s) found across 5 data rows. No records were persisted."
  }
}
```

---

### `GET /api/v1/projects/{project_id}/analytics/summary`
- **Purpose**: Compute review metrics (total reviews, average rating, rating distribution 1-5).
- **Success Status**: `200 OK`
- **Possible Errors**: `404 Not Found`
- **Response**:
```json
{
  "project_id": 1,
  "project_name": "Grocery Delivery",
  "total_reviews": 10,
  "average_rating": 4.2,
  "rating_counts": {
    "1": 1,
    "2": 1,
    "3": 1,
    "4": 2,
    "5": 5
  }
}
```
