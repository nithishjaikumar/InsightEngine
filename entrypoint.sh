#!/bin/sh
set -e

echo "Applying database migrations with Alembic..."
alembic upgrade head

echo "Starting InsightEngine Uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
