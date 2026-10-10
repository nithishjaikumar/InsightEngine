# InsightEngine — Production Deployment Guide

This guide covers deployment procedures for containerized and cloud production environments.

---

## 1. Cloud Architecture & Hosting Strategy

InsightEngine is designed to be deployed as a containerized web service connecting to a managed MySQL instance:

```mermaid
graph LR
    User[Client Application] -->|HTTPS| Proxy[Cloud Ingress / CDN]
    Proxy -->|Reverse Proxy Port 8000| Service[FastAPI Web Service: Render / AWS / Docker]
    Service -->|TCP 3306 TLS| DB[(Managed MySQL 8: Aiven / TiDB Cloud / AWS RDS)]
```

### Provider Comparison (Cost, Free-Tier & Compatibility):

| Provider | Component | Cost / Free Tier | Python & MySQL Compatibility | TLS & Persistence | Selection Notes |
|---|---|---|---|---|---|
| **Render** | API Compute | Free Tier (512MB RAM, spins down on idle) | Full Dockerfile / Python 3.12 support | Automatic HTTPS on `*.onrender.com` | **Recommended for Compute**: 1-click Blueprint via `render.yaml`, automated health check, non-root Docker runtime. |
| **Aiven** | Managed MySQL | Free Tier (1 CPU, 1GB RAM, 1GB disk) | MySQL 8.0 standard protocol | TLS enforced, persistent storage, automated backups | **Recommended for Database**: Zero credit card required on signup, true managed MySQL 8. |
| **TiDB Cloud** | Managed MySQL | Free Tier Serverless (5GB storage, 50M request units/mo) | MySQL 8.0 wire-compatible | TLS enforced (`ssl_disabled=False`), persistent storage | Excellent free alternative. |
| **Railway** | Compute + DB | $5 trial credit, then usage-based ($5/mo) | Docker & 1-click MySQL template | Private networking between services | Good paid option if unified single-platform hosting is desired. |

---

## 2. Production Configuration & Environment Variables

Never commit `.env` to source control. Set the following environment variables in your cloud dashboard or secret store:

| Variable | Recommended Production Value | Description |
|---|---|---|
| `APP_NAME` | `InsightEngine` | Service identifier |
| `APP_ENV` | `production` | Environment mode (`production`, `staging`, `development`) |
| `DATABASE_URL` | `mysql+pymysql://<user>:<password>@<cloud-host>:<port>/<database>?ssl_disabled=False` | Full MySQL connection URI with PyMySQL driver |
| `API_V1_PREFIX` | `/api/v1` | Versioned API route prefix |
| `MAX_UPLOAD_SIZE_MB` | `5` | Maximum file size for CSV ingestion |
| `MAX_CSV_ROWS` | `5000` | Maximum rows allowed per CSV upload |

---

## 3. Step-by-Step Cloud Deployment Procedure

### Phase A: Managed Cloud MySQL Provisioning (Requires User Account)
1. **Sign up at [Aiven.io](https://aiven.io)** (or [TiDB Cloud](https://tidbcloud.com)). No credit card required.
2. Click **Create Service** -> Select **MySQL** -> Choose Cloud Region (e.g. AWS or GCP closest to your users) -> Select the **Free Tier**.
3. Once provisioned (typically takes 2-3 minutes):
   - Note the **Host**, **Port**, **User**, **Password**, and **Database Name** (default is usually `defaultdb`).
   - Create a database named `insightengine` if desired, or use the default database name.
   - Construct your connection string:
     ```text
     mysql+pymysql://<user>:<password>@<host>:<port>/<dbname>?ssl_disabled=False
     ```

### Phase B: Push Repository to GitHub
1. Create a new private or public repository on [GitHub](https://github.com/new) (e.g. `InsightEngine`).
2. Link your local repository and push:
   ```bash
   git remote add origin https://github.com/<your-username>/InsightEngine.git
   git branch -M main
   git push -u origin main
   ```

### Phase C: Deploy to Render via Blueprint (`render.yaml`)
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** -> **Blueprint**.
3. Select your `InsightEngine` GitHub repository.
4. Render will detect `render.yaml` and configure:
   - Web service name: `insightengine-api`
   - Runtime: Docker (`Dockerfile`)
   - Health check: `/health`
5. Under environment variables, Render will prompt for `DATABASE_URL`:
   - Paste your cloud MySQL connection string:
     `mysql+pymysql://<user>:<password>@<host>:<port>/<dbname>?ssl_disabled=False`
6. Click **Apply**.
7. The container starts automatically:
   - `entrypoint.sh` executes `alembic upgrade head`, creating the `projects`, `reviews`, and `alembic_version` tables in your cloud MySQL database.
   - Uvicorn launches on port 8000 and serves traffic through Render's HTTPS reverse proxy.

---

## 4. Public Deployment Verification Sequence

Once Render deploys your service (e.g. `https://insightengine-api.onrender.com`), verify it with these exact steps:

### 1. Verify Health Check
```bash
curl -f https://<your-service-domain>/health
# Expected: {"status":"ok","app":"InsightEngine","environment":"production"}
```

### 2. Verify Swagger Documentation
Open `https://<your-service-domain>/docs` in your browser.

### 3. Create Smoke-Test Project
```bash
curl -X POST https://<your-service-domain>/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Public Verification", "description": "Cloud deployment verification project"}'
```

### 4. Create Review Under Project
```bash
curl -X POST https://<your-service-domain>/api/v1/projects/1/reviews \
  -H "Content-Type: application/json" \
  -d '{"customer_name": "QA Auditor", "rating": 5, "review_text": "Live cloud deployment verified with persistent MySQL!"}'
```

### 5. Ingest Sample CSV
```bash
curl -X POST https://<your-service-domain>/api/v1/projects/1/reviews/import-csv \
  -F "file=@sample_data/sample_reviews.csv"
```

### 6. Verify Feedback Analytics
```bash
curl https://<your-service-domain>/api/v1/projects/1/analytics/summary
```

### 7. Clean Up Smoke Test Entities
```bash
# Delete reviews then delete project
curl -X DELETE https://<your-service-domain>/api/v1/projects/1
```

---

## 5. Security & Secret Management

- **Zero Credential Commits**: The repository is protected by `.gitignore`. Local `.env` files and MySQL passwords are never committed.
- **SSL/TLS**: Remote connections to cloud MySQL require encrypted transmission. The PyMySQL parameter `ssl_disabled=False` ensures TLS handshake is enforced.
- **Container Isolation**: The `Dockerfile` drops root privileges and executes as `appuser` (UID 1000).
- **Sanitized Errors**: The application captures database errors globally without exposing SQL tracebacks or table schema to public API consumers.
