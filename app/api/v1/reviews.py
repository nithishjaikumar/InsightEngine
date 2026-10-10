from typing import Optional
from fastapi import APIRouter, status, Query
from app.api.dependencies import DatabaseSession, PaginationDep
from app.schemas.review import ReviewResponse, ReviewUpdate
from app.schemas.common import PaginatedResponse
from app.services import review_service

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get(
    "",
    response_model=PaginatedResponse[ReviewResponse],
    status_code=status.HTTP_200_OK,
    summary="List reviews across all projects",
    description="Retrieve paginated reviews across projects with optional filters for project ID, rating, and text search.",
)
def list_reviews(
    pagination: PaginationDep,
    db: DatabaseSession,
    project_id: Optional[int] = Query(default=None, description="Filter by project ID"),
    rating: Optional[int] = Query(default=None, ge=1, le=5, description="Filter by rating (1-5)"),
    search: Optional[str] = Query(default=None, description="Search term in review text or customer name"),
) -> PaginatedResponse[ReviewResponse]:
    items, total = review_service.get_reviews(
        db=db,
        limit=pagination.limit,
        offset=pagination.offset,
        project_id=project_id,
        rating=rating,
        search=search,
    )
    return PaginatedResponse(
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
        items=items,
    )


@router.get(
    "/{review_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get review by ID",
    description="Retrieve a single review by its ID.",
)
def get_review(review_id: int, db: DatabaseSession) -> ReviewResponse:
    return review_service.get_review_by_id(db=db, review_id=review_id)


@router.patch(
    "/{review_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Update review",
    description="Partially update a review's rating, text, or customer name.",
)
def update_review(
    review_id: int,
    review_in: ReviewUpdate,
    db: DatabaseSession,
) -> ReviewResponse:
    return review_service.update_review(db=db, review_id=review_id, review_in=review_in)


@router.delete(
    "/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete review",
    description="Delete a customer review by its ID.",
)
def delete_review(review_id: int, db: DatabaseSession) -> None:
    review_service.delete_review(db=db, review_id=review_id)
