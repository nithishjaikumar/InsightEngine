# InsightEngine — Technical Interview & Mentorship Guide

This guide prepares you to present, explain, and defend every engineering decision made in **InsightEngine** during a senior backend engineering interview.

---

## 1. Project Pitches

### The 30-Second Elevator Pitch
> *"InsightEngine is a high-performance REST API built with FastAPI and MySQL that organizes and analyzes consumer feedback by project. It solves the operational challenge of feedback ingestion by offering atomic, bulk CSV review uploads, strict relational constraints to prevent data orphaning, defense-in-depth request validation with Pydantic, and comprehensive test coverage. I built it as a clean modular monolith adhering to production-ready design patterns like connection pooling, safe migrations with Alembic, and zero credential leakage."*

### The 2-Minute Architecture Pitch
> *"In consumer-facing platforms, customer reviews are frequently fragmented across spreadsheets, third-party forms, and disparate internal systems. InsightEngine provides a unified backend API to capture and analyze this data.
>
> Architecturally, it is designed as a modular monolith with strict layer separation:
> 1. **Transport Layer**: FastAPI handles routing, dependency injection, and automatic OpenAPI documentation.
> 2. **Validation Layer**: Pydantic schemas enforce type safety, string sanitization, and value boundaries before anything touches business logic.
> 3. **Service Layer**: Handles core domain rules such as unique project names, restrictive project deletion policies (preventing accidental deletion of projects that contain feedback), and bulk CSV processing.
> 4. **Persistence Layer**: SQLAlchemy 2.0 manages database sessions and connection pooling over MySQL 8, with Alembic handling schema versioning.
>
> A key engineering highlight is our **atomic CSV ingestion pipeline**: when clients upload bulk feedback files, we parse them in streaming chunks, validate every single row against rating and text constraints, and execute the entire batch within a database transaction. If even a single row fails, we roll back the entire transaction and return a clear, row-indexed diagnostic report, ensuring zero partial data corruption.
>
> The codebase has 100% automated test coverage across CRUD, validation bounds, atomic rollbacks, and error scenarios using pytest and TestClient."*

---

## 2. Core Architectural & Technology Decisions

### Why FastAPI over Django or Flask?
- **Asynchronous & Fast**: Native ASGI support with Starlette foundations allows high I/O throughput.
- **Pydantic Integration**: Automatic serialization, data casting, and OpenAPI/Swagger documentation generation out of the box.
- **Dependency Injection**: First-class `Depends()` system makes managing database sessions and pagination modular and easy to mock during tests.

### Why MySQL 8?
- **Relational Integrity**: Feedback data naturally maps to a 1-to-many relationship with foreign keys (`projects.id -> reviews.project_id`).
- **ACID Transactions**: Vital for ensuring atomic bulk imports.
- **Native Check Constraints**: MySQL 8 actively enforces check constraints like `rating >= 1 AND rating <= 5` at the storage layer.

### Why SQLAlchemy 2.0?
- Modern SQLAlchemy 2.0 adopts type-hinted `Mapped` and `mapped_column`, making models self-documenting and type-checked with Mypy.
- Uses `select()` query constructs, making queries explicit and composable rather than relying on legacy `Query` syntax.

---

## 3. 20+ Technical Interview Questions & In-Depth Answers

### Q1: How do you handle database sessions across concurrent requests in FastAPI?
**Answer**: We use FastAPI's dependency injection system via `get_db()`. Each incoming HTTP request receives its own isolated SQLAlchemy `Session` from the connection pool. The dependency uses Python's generator syntax (`yield db`) wrapped in a `try...except...finally` block. If an unhandled exception occurs, `db.rollback()` is executed. In the `finally` block, `db.close()` guarantees that the connection is checked back into the pool regardless of whether the request succeeded or failed.

### Q2: What prevents MySQL connection drops when the database is idle?
**Answer**: MySQL terminates idle connections after `wait_timeout` (typically 8 hours, or shorter in clouds). We configure the SQLAlchemy engine with `pool_pre_ping=True`, which issues a lightweight `SELECT 1` ping before handing a pooled connection to the worker. If the socket has died, SQLAlchemy transparently recycles it. We also configure `pool_recycle=3600` to refresh connections every hour.

### Q3: Why did you choose a restrictive deletion policy for projects instead of CASCADE DELETE?
**Answer**: Customer feedback is valuable historical business intelligence. If an administrative user accidentally deletes a project, a cascade delete would permanently eradicate thousands of customer reviews. We implemented `ON DELETE RESTRICT` at the database level and an explicit pre-deletion check in `project_service.delete_project`. If a project has reviews, the API halts with `HTTP 409 Conflict`, requiring explicit business intervention before reviews can be lost.

### Q4: How does the CSV import ensure atomicity?
**Answer**: We implement a strict atomic validation policy. We read and validate the entire CSV into memory/buffer before touching the database. We evaluate every row's headers, ratings (1-5), and review text. If any row contains an error, we immediately raise an HTTP exception containing all row-indexed errors and persist nothing. Furthermore, the database insert is wrapped in a SQLAlchemy transaction; if a database flush or commit fails, `db.rollback()` guarantees zero partial records are stored.

### Q5: How do you protect against Denial of Service (DoS) from large file uploads?
**Answer**: In `validate_and_read_csv_file`, we stream the upload in 1MB chunks instead of reading the entire file into memory with `file.read()`. We accumulate a running byte counter against `settings.max_upload_size_bytes` (5MB). If the size exceeds the limit, we abort immediately with `HTTP 413 Content Too Large`. We also enforce `MAX_CSV_ROWS` (5,000) during parsing.

### Q6: How do you prevent SQL injection in InsightEngine?
**Answer**: We use SQLAlchemy 2.0 parameterized queries via `select(...)` and ORM mapping. SQLAlchemy automatically binds parameters to placeholders in the compiled SQL statements, completely isolating user input from SQL syntax. Even in search queries, we use `.ilike(f"%{search}%")`, where the search string is bound as a parameter rather than concatenated into raw SQL.

### Q7: Why do you validate ratings in both Pydantic and MySQL?
**Answer**: Defense-in-depth. Pydantic validates incoming requests at the application boundary, giving immediate, user-friendly `HTTP 422` feedback without incurring database latency. However, database check constraints (`CHECK (rating >= 1 AND rating <= 5)`) guarantee data integrity against direct database modifications, scripts, or migrations that bypass the API.

### Q8: What is the difference between PATCH and PUT in REST, and why did you use PATCH?
**Answer**: `PUT` represents a complete resource replacement, meaning any omitted field would be reset to null or its default. `PATCH` represents partial modification. For both projects and reviews, users often want to update only a name or review text without resending all existing fields. We implemented `PATCH` using Pydantic models with optional fields and update only the provided values.

### Q9: Why do you have separate Pydantic schemas for Create, Update, and Response?
**Answer**: Separation of concerns and security. `ProjectCreate` requires `name`. `ProjectUpdate` makes all fields optional for partial updates. `ProjectResponse` includes server-generated attributes (`id`, `created_at`, `updated_at`) and excludes internal fields. This prevents mass-assignment vulnerabilities where a malicious client might try to send `id` or `created_at` in the request body.

### Q10: How do you handle database credentials securely across environments?
**Answer**: We use `pydantic-settings` to load configuration from environment variables, falling back to a `.env` file that is strictly ignored by `.gitignore`. No credentials or connection strings are ever committed to source control. In Docker and cloud environments, credentials are provided via platform secrets or environment injection.

### Q11: How do your automated tests run without corrupting a real MySQL database?
**Answer**: In `tests/conftest.py`, we override FastAPI's `get_db` dependency using an isolated in-memory SQLite database (`sqlite:///:memory:`) with `StaticPool`. We enable `PRAGMA foreign_keys=ON` to mirror relational constraints. Each test gets a fresh schema via `Base.metadata.create_all()` and cleans up with `Base.metadata.drop_all()`. This allows rapid, deterministic test execution with zero side effects on developer or production databases.

### Q12: Why use Alembic instead of `Base.metadata.create_all()` in production?
**Answer**: `Base.metadata.create_all()` only creates tables if they do not already exist; it cannot alter existing tables, add columns, rename fields, or drop constraints without manual intervention. Alembic generates timestamped, version-controlled migration scripts that can safely apply forward upgrades and backward rollbacks across multiple environments.

### Q13: How does your error handling prevent information leakage?
**Answer**: In `app/main.py`, we registered a global exception handler for `SQLAlchemyError`. If an unexpected database exception occurs, the server logs the detailed traceback internally for diagnostics, but returns a generic message to the client: `{"detail": "A database error occurred. Your request could not be processed."}`. This prevents attackers from learning internal table names, column structures, or database engine versions.

### Q14: Explain the difference between `scalar()`, `scalars()`, and `execute()` in SQLAlchemy 2.0.
**Answer**:
- `db.execute(stmt)` returns a `Result` object containing row tuples.
- `db.scalars(stmt)` returns a `ScalarResult` object that unwraps the first column of each row (ideal for ORM model instances).
- `db.scalar(stmt)` returns the first column of the first row directly (ideal for count queries like `select(func.count())`).

### Q15: How does your pagination work, and what edge cases does it protect against?
**Answer**: We use limit-offset pagination defined in `PaginationParams`. We enforce boundaries: `limit` must be between 1 and 100 (`ge=1, le=100`), preventing clients from querying millions of records and exhausting server memory. `offset` must be non-negative (`ge=0`). The endpoint returns both `total` items and the current page items in a standardized `PaginatedResponse` schema.

### Q16: How do you prevent duplicate project names under race conditions?
**Answer**: We enforce uniqueness at two levels: the application service checks `get_project_by_name` and returns an explicit `HTTP 409 Conflict`. To handle concurrent requests that race past the service check, the database table has a unique index on `projects(name)`. If a duplicate is inserted concurrently, the database raises an `IntegrityError`, which rolls back the transaction.

### Q17: What does `from_attributes=True` do in Pydantic v2?
**Answer**: In Pydantic v2 (previously `orm_mode = True` in v1), `from_attributes=True` allows Pydantic models to extract data from arbitrary Python objects using attribute access (`obj.id`) instead of dictionary key access (`obj["id"]`). This allows direct serialization of SQLAlchemy ORM entities into response schemas.

### Q18: What is the lifespan context manager in FastAPI?
**Answer**: Introduced in modern FastAPI/Starlette to replace deprecated `@app.on_event("startup")` and `"shutdown"` decorators. It uses an async context manager: code before `yield` runs on application startup, and code after `yield` runs gracefully during application shutdown.

### Q19: How would you scale InsightEngine if traffic grew to 10,000 requests/sec?
**Answer**:
1. **Stateless API horizontal scaling**: Run multiple container instances behind a load balancer (e.g. AWS ALB or Nginx).
2. **Database Read Replicas**: Route read-heavy queries (`GET /projects`, `GET /reviews`) to MySQL read replicas, directing writes (`POST`, `PATCH`, `DELETE`) to the primary database.
3. **Caching**: Place a Redis cache in front of frequently accessed endpoints like `GET /projects/{id}/analytics/summary`.
4. **Asynchronous CSV Ingestion**: Offload CSV processing to background workers (e.g., Celery or ARQ) with message queues (RabbitMQ/Redis) for files larger than 10MB.

### Q20: What are the current limitations of InsightEngine and what would be your next steps?
**Answer**:
1. **Authentication & Authorization**: Currently open without API keys or JWT tokens. Next step: add OAuth2 with role-based access control (Admin vs Viewer).
2. **Sentiment Analysis**: Currently relies purely on numeric ratings. Next step: integrate asynchronous text sentiment scoring using lightweight open-source NLP.
3. **Asynchronous Ingestion**: For enterprise-scale files (>50,000 rows), migrate from synchronous request handling to background task processing with webhook or polling status.
