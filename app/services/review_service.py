from typing import Optional, Tuple, List
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.project import Project
from app.models.review import Review
from app.schemas.review import ReviewCreate, ReviewUpdate
from app.services.project_service import get_project_by_id


def get_review_by_id(db: Session, review_id: int) -> Review:
    """Retrieve a single review by primary key or raise 404."""
    review = db.get(Review, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with ID {review_id} not found",
        )
    return review


def create_review(db: Session, project_id: int, review_in: ReviewCreate) -> Review:
    """Create a new review belonging to an existing project."""
    # Ensure project exists; raises 404 if not found
    get_project_by_id(db, project_id)

    review = Review(
        project_id=project_id,
        customer_name=review_in.customer_name,
        rating=review_in.rating,
        review_text=review_in.review_text,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def get_reviews_for_project(
    db: Session,
    project_id: int,
    limit: int = 20,
    offset: int = 0,
    rating: Optional[int] = None,
    search: Optional[str] = None,
) -> Tuple[List[Review], int]:
    """Retrieve paginated reviews for a specific project with optional rating and search filters."""
    # Ensure project exists first (raises 404 if missing)
    get_project_by_id(db, project_id)

    base_query = select(Review).where(Review.project_id == project_id)
    count_query = select(func.count()).select_from(Review).where(Review.project_id == project_id)

    if rating is not None:
        base_query = base_query.where(Review.rating == rating)
        count_query = count_query.where(Review.rating == rating)

    if search:
        search_pattern = f"%{search.strip()}%"
        filter_expr = Review.review_text.ilike(search_pattern) | Review.customer_name.ilike(search_pattern)
        base_query = base_query.where(filter_expr)
        count_query = count_query.where(filter_expr)

    total = db.scalar(count_query) or 0
    items_stmt = base_query.order_by(Review.created_at.desc(), Review.id.desc()).offset(offset).limit(limit)
    items = list(db.scalars(items_stmt).all())
    return items, total


def get_reviews(
    db: Session,
    limit: int = 20,
    offset: int = 0,
    project_id: Optional[int] = None,
    rating: Optional[int] = None,
    search: Optional[str] = None,
) -> Tuple[List[Review], int]:
    """Retrieve paginated reviews across all projects with filters."""
    base_query = select(Review)
    count_query = select(func.count()).select_from(Review)

    if project_id is not None:
        base_query = base_query.where(Review.project_id == project_id)
        count_query = count_query.where(Review.project_id == project_id)

    if rating is not None:
        base_query = base_query.where(Review.rating == rating)
        count_query = count_query.where(Review.rating == rating)

    if search:
        search_pattern = f"%{search.strip()}%"
        filter_expr = Review.review_text.ilike(search_pattern) | Review.customer_name.ilike(search_pattern)
        base_query = base_query.where(filter_expr)
        count_query = count_query.where(filter_expr)

    total = db.scalar(count_query) or 0
    items_stmt = base_query.order_by(Review.created_at.desc(), Review.id.desc()).offset(offset).limit(limit)
    items = list(db.scalars(items_stmt).all())
    return items, total


def update_review(db: Session, review_id: int, review_in: ReviewUpdate) -> Review:
    """Partially update review fields."""
    review = get_review_by_id(db, review_id)

    if review_in.customer_name is not None:
        review.customer_name = review_in.customer_name

    if review_in.rating is not None:
        review.rating = review_in.rating

    if review_in.review_text is not None:
        review.review_text = review_in.review_text

    db.commit()
    db.refresh(review)
    return review


def delete_review(db: Session, review_id: int) -> None:
    """Delete an individual review."""
    review = get_review_by_id(db, review_id)
    db.delete(review)
    db.commit()
