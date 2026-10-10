from typing import Optional
from fastapi import APIRouter, status, UploadFile, File, Query
from app.api.dependencies import DatabaseSession, PaginationDep
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.schemas.review import (
    ReviewCreate,
    ReviewResponse,
    CsvImportResponse,
    ProjectAnalyticsSummary,
)
from app.schemas.common import PaginatedResponse
from app.services import project_service, review_service
from app.services.csv_import_service import validate_and_read_csv_file, process_csv_import

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
    description="Creates a new project for feedback aggregation. Fails with 409 if name already exists.",
)
def create_project(project_in: ProjectCreate, db: DatabaseSession) -> ProjectResponse:
    return project_service.create_project(db=db, project_in=project_in)


@router.get(
    "",
    response_model=PaginatedResponse[ProjectResponse],
    status_code=status.HTTP_200_OK,
    summary="List all projects",
    description="Retrieve paginated list of all projects with total count.",
)
def list_projects(
    pagination: PaginationDep,
    db: DatabaseSession,
) -> PaginatedResponse[ProjectResponse]:
    items, total = project_service.get_projects(
        db=db,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return PaginatedResponse(
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
        items=items,
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Get project by ID",
    description="Retrieve a specific project by its ID.",
)
def get_project(project_id: int, db: DatabaseSession) -> ProjectResponse:
    return project_service.get_project_by_id(db=db, project_id=project_id)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Update project",
    description="Partially update a project name and/or description.",
)
def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    db: DatabaseSession,
) -> ProjectResponse:
    return project_service.update_project(db=db, project_id=project_id, project_in=project_in)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
    description="Deletes a project only if it has no reviews. Returns 409 if reviews exist.",
)
def delete_project(project_id: int, db: DatabaseSession) -> None:
    project_service.delete_project(db=db, project_id=project_id)


# --- Nested Review Endpoints under Project ---

@router.post(
    "/{project_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create review for project",
    description="Add a new customer review to an existing project.",
)
def create_project_review(
    project_id: int,
    review_in: ReviewCreate,
    db: DatabaseSession,
) -> ReviewResponse:
    return review_service.create_review(db=db, project_id=project_id, review_in=review_in)


@router.get(
    "/{project_id}/reviews",
    response_model=PaginatedResponse[ReviewResponse],
    status_code=status.HTTP_200_OK,
    summary="List reviews for project",
    description="Retrieve paginated reviews for a specific project with optional rating and search filters.",
)
def list_project_reviews(
    project_id: int,
    pagination: PaginationDep,
    db: DatabaseSession,
    rating: Optional[int] = Query(default=None, ge=1, le=5, description="Filter by rating (1-5)"),
    search: Optional[str] = Query(default=None, description="Search term in review text or customer name"),
) -> PaginatedResponse[ReviewResponse]:
    items, total = review_service.get_reviews_for_project(
        db=db,
        project_id=project_id,
        limit=pagination.limit,
        offset=pagination.offset,
        rating=rating,
        search=search,
    )
    return PaginatedResponse(
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
        items=items,
    )


@router.post(
    "/{project_id}/reviews/import-csv",
    response_model=CsvImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Import reviews from CSV",
    description=(
        "Atomic ingestion of reviews from a CSV file. "
        "Strict policy: if any row is invalid, the entire file is rejected and no rows are saved."
    ),
)
async def import_reviews_csv(
    project_id: int,
    db: DatabaseSession,
    file: UploadFile = File(..., description="Multipart CSV file containing rating, review_text, customer_name"),
) -> CsvImportResponse:
    content = await validate_and_read_csv_file(file)
    return process_csv_import(db=db, project_id=project_id, csv_content=content)


@router.get(
    "/{project_id}/analytics/summary",
    response_model=ProjectAnalyticsSummary,
    status_code=status.HTTP_200_OK,
    summary="Project feedback analytics summary",
    description="Computes total reviews, average rating, and rating distribution for the project.",
)
def get_project_analytics(
    project_id: int,
    db: DatabaseSession,
) -> ProjectAnalyticsSummary:
    return project_service.get_project_analytics(db=db, project_id=project_id)
