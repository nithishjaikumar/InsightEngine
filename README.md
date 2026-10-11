# InsightEngine — Consumer Feedback Analysis API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.15-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Tests](https://img.shields.io/badge/Tests-30%20Passed-brightgreen?logo=pytest)](https://docs.pytest.org/)

InsightEngine is a production-grade Python REST API that organizes customer feedback by project, enforces relational database integrity in MySQL, validates data schemas via Pydantic, and provides atomic CSV feedback ingestion and analytics.

---

## 1. Problem Statement & Features

### Problem Statement
Product and customer success teams receive user feedback through multiple fragmented channels (support emails, customer surveys, CSV spreadsheets, and app reviews). Without a centralized system, feedback is hard to correlate, duplicate projects are created, reviews get accidentally orphaned or deleted, and bulk data imports frequently fail halfway through, corrupting data integrity.

### Key Features
- **Project & Review Management**: Full CRUD operations for projects and consumer reviews with clean foreign-key relationships.
- **Relational Integrity & Safeguards**:
  - Unique project names (HTTP 409 conflict on duplicate).
  - Restrictive project deletion policy: projects containing reviews cannot be accidentally deleted (HTTP 409 conflict).
  - Rating boundary enforcement (1 to 5) at both Pydantic and MySQL database check-constraint layers.
- **Atomic Bulk CSV Ingestion**: Multipart CSV upload supporting up to 5,000 rows. Strict atomic policy: if any row fails validation, the entire batch is rejected with zero partial data written.
- **Dynamic Feedback Analytics**: Real-time aggregation endpoint computing total reviews, average rating, and 1-to-5 star distribution.
- **Defense-in-Depth Validation**: Pydantic v2 schemas reject blank strings, invalid numbers, and malicious payloads before database execution.
- **Automated Test Suite**: 30 comprehensive automated tests covering all CRUD operations, boundary conditions, foreign-key rules, error handling, and CSV rollbacks.

---

## 2. Architecture & Data Model

### Architecture Diagram
```mermaid
graph TD
    Client([Client / Frontend / HTTP]) -->|HTTP Request| FastAPI[FastAPI REST API]
    FastAPI -->|Request Validation| Pydantic[Pydantic v2 Schemas]
    Pydantic -->|Clean DTO| Services[Service Layer: Projects / Reviews / CSV]
    Services -->|Unit of Work| SQLAlchemy[SQLAlchemy 2.0 ORM]
    SQLAlchemy -->|Connection Pool| MySQL[(MySQL 8 Database)]
    MySQL -->|Persisted State| SQLAlchemy
    SQLAlchemy -->|Model Entities| Services
    Services -->|Response Serialization| Pydantic
    Pydantic -->|HTTP 200/201 JSON| Client
```

### Entity-Relationship (ER) Diagram
```mermaid
erDiagram
    PROJECTS ||--o{ REVIEWS : "has many"
    PROJECTS {
        int id PK "Auto-increment"
        varchar_100 name UK "Unique index"
        text description "Optional"
        datetime created_at "Indexed"
        datetime updated_at "UTC update"
    }
    REVIEWS {
        int id PK "Auto-increment"
        int project_id FK "References projects(id) ON DELETE RESTRICT"
        varchar_100 customer_name "Optional"
        int rating "Check constraint 1..5"
        text review_text "Required"
        datetime created_at "Indexed"
        datetime updated_at "UTC update"
    }
```

---

## 3. Technology Stack

- **Language**: Python 3.12+ (tested on Python 3.12 and Python 3.15)
- **Web Framework**: FastAPI & Uvicorn
- **Database**: MySQL 8.0 (Primary production database)
- **ORM**: SQLAlchemy 2.0+ (Modern `Mapped` syntax and 2.0 style queries)
- **Driver**: PyMySQL
- **Schema Migrations**: Alembic
- **Validation**: Pydantic v2 & Pydantic Settings
- **Testing**: pytest & FastAPI TestClient (HTTPX)
- **File Uploads**: python-multipart & Python standard library `csv`

---

## 4. Local Development Setup

### Prerequisites
- Python 3.12 or compatible installed
- MySQL 8 installed or Docker available

### Step 1: Clone and Navigate to Directory
```bash
cd d:/Project/InsightEngine
```

### Step 2: Create and Activate Virtual Environment
**Windows PowerShell:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` with your MySQL credentials:
```ini
APP_NAME=InsightEngine
APP_ENV=development
API_V1_PREFIX=/api/v1
DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/insightengine
MAX_UPLOAD_SIZE_MB=5
MAX_CSV_ROWS=5000
```

### Step 5: Initialize MySQL Database & Run Migrations
Create the database in MySQL:
```sql
CREATE DATABASE insightengine CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Run migrations via Alembic:
```bash
alembic upgrade head
```

### Step 6: Start Application Server
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Interactive Swagger Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Alternative ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- Health Check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### Quick Start — Dashboard

**Backend** — run in the first terminal:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Dashboard** — run in a second terminal:

```powershell
.\dashboard-venv\Scripts\python.exe -m streamlit run dashboard.py
```

| Resource | Link |
|---|---|
| Dashboard | [Open Dashboard](http://localhost:8501) |
| API Documentation | [Swagger UI](http://127.0.0.1:8000/docs) |
| Health Check | [Health Check](http://127.0.0.1:8000/health) |

*MySQL must be running before starting the backend.*

---

## 5. Running Automated Tests

InsightEngine includes 30 automated tests in `tests/` with zero side effects on your real database:

```bash
pytest -v
```

Expected result:
```
tests/test_csv_import.py .......... [ 33%]
tests/test_projects.py ...........   [ 70%]
tests/test_reviews.py .........     [100%]
======================= 30 passed in 1.01s =======================
```

---

## 6. API Endpoint Summary

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| `GET` | `/health` | Application health check | `200` |
| `POST` | `/api/v1/projects` | Create a new project (name must be unique) | `201` / `409` |
| `GET` | `/api/v1/projects` | List projects (pagination: `limit`, `offset`) | `200` |
| `GET` | `/api/v1/projects/{id}` | Get project details | `200` / `404` |
| `PATCH` | `/api/v1/projects/{id}` | Partial update of project name/description | `200` / `404` / `409` |
| `DELETE` | `/api/v1/projects/{id}` | Delete project (restricted if reviews exist) | `204` / `404` / `409` |
| `POST` | `/api/v1/projects/{id}/reviews` | Create a review under a project | `201` / `404` / `422` |
| `GET` | `/api/v1/projects/{id}/reviews` | List reviews for project (filters: `rating`, `search`) | `200` / `404` |
| `POST` | `/api/v1/projects/{id}/reviews/import-csv` | Atomically import reviews from CSV file | `200` / `400` / `413` |
| `GET` | `/api/v1/projects/{id}/analytics/summary` | Feedback analytics summary for project | `200` / `404` |
| `GET` | `/api/v1/reviews` | List reviews across projects (filter by `project_id`, `rating`, `search`) | `200` |
| `GET` | `/api/v1/reviews/{id}` | Get single review | `200` / `404` |
| `PATCH` | `/api/v1/reviews/{id}` | Partial update of review rating, text, or customer name | `200` / `404` / `422` |
| `DELETE` | `/api/v1/reviews/{id}` | Delete a review | `204` / `404` |

---

## 7. CSV Upload Instructions

InsightEngine accepts standard CSV files with the following headers:
```csv
customer_name,rating,review_text
Alice Smith,5,"The grocery delivery was lightning fast!"
Bob Jones,4,"Great customer service."
```

### Uploading via cURL:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/projects/1/reviews/import-csv \
  -F "file=@sample_data/sample_reviews.csv"
```

### Uploading via Python `httpx`:
```python
import httpx

with open("sample_data/sample_reviews.csv", "rb") as f:
    files = {"file": ("sample_reviews.csv", f, "text/csv")}
    response = httpx.post("http://127.0.0.1:8000/api/v1/projects/1/reviews/import-csv", files=files)
    print(response.json())
```

---

## 8. Docker Deployment

Deploy the entire stack with a single command using Docker Compose:

```bash
docker-compose up --build -d
```

This starts:
- `insightengine_db`: MySQL 8 with persistent storage in Docker volume `mysql_data`.
- `insightengine_api`: Containerized FastAPI application with non-root security and automated health checks.

---

## 9. Technical Documentation Directory

Deep dive into the architecture, database design, and interview preparation:
- [System Architecture & Request Lifecycle](docs/ARCHITECTURE.md)
- [Relational Database & Migrations Guide](docs/DATABASE_GUIDE.md)
- [Complete REST API Reference](docs/API_REFERENCE.md)
- [Technical Interview & Mentorship Guide (20+ Q&As)](docs/INTERVIEW_GUIDE.md)
- [Production Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
