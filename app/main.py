import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.api.v1.router import api_v1_router

# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("insightengine")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    logger.info("Starting up %s in '%s' mode...", settings.APP_NAME, settings.APP_ENV)
    yield
    logger.info("Shutting down %s...", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description="Consumer Feedback Analysis API - Manage projects, ingest customer reviews atomically, and query feedback analytics.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handle unexpected database errors safely.
    Prevents leaking SQL statements, connection strings, credentials, or internal schema traces.
    """
    logger.error("Database operational error during %s %s: %s", request.method, request.url.path, str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "A database error occurred. Your request could not be processed."},
    )


# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Application Health Check",
    description="Returns the current operating status and environment metadata.",
)
def health_check() -> dict:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


# Include API v1 router
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)
