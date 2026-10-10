from typing import Optional, Tuple, List, Dict
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.project import Project
from app.models.review import Review
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.review import ProjectAnalyticsSummary


def get_project_by_id(db: Session, project_id: int) -> Project:
    """Retrieve a project by its primary key or raise 404."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found",
        )
    return project


def get_project_by_name(db: Session, name: str) -> Optional[Project]:
    """Retrieve a project by its unique name."""
    stmt = select(Project).where(Project.name == name)
    return db.scalars(stmt).first()


def create_project(db: Session, project_in: ProjectCreate) -> Project:
    """Create a new project ensuring name uniqueness."""
    existing = get_project_by_name(db, project_in.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A project with name '{project_in.name}' already exists",
        )

    project = Project(
        name=project_in.name,
        description=project_in.description,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_projects(db: Session, limit: int = 20, offset: int = 0) -> Tuple[List[Project], int]:
    """Retrieve paginated list of projects and total count."""
    count_stmt = select(func.count()).select_from(Project)
    total = db.scalar(count_stmt) or 0

    stmt = select(Project).order_by(Project.id.asc()).offset(offset).limit(limit)
    items = list(db.scalars(stmt).all())
    return items, total


def update_project(db: Session, project_id: int, project_in: ProjectUpdate) -> Project:
    """Update project fields with duplicate name checking."""
    project = get_project_by_id(db, project_id)

    if project_in.name is not None and project_in.name != project.name:
        existing = get_project_by_name(db, project_in.name)
        if existing and existing.id != project_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A project with name '{project_in.name}' already exists",
            )
        project.name = project_in.name

    if project_in.description is not None:
        project.description = project_in.description

    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int) -> None:
    """
    Delete a project only when it has no associated reviews.
    Enforces a strict restrictive deletion policy (returns 409 if reviews exist).
    """
    project = get_project_by_id(db, project_id)

    # Check whether reviews exist for this project
    review_count_stmt = select(func.count()).select_from(Review).where(Review.project_id == project_id)
    review_count = db.scalar(review_count_stmt) or 0

    if review_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete project {project_id} because it contains {review_count} "
                "existing review(s). Deleting projects with reviews is restricted to protect customer feedback."
            ),
        )

    db.delete(project)
    db.commit()


def get_project_analytics(db: Session, project_id: int) -> ProjectAnalyticsSummary:
    """Calculate review statistics and rating distributions for a project."""
    project = get_project_by_id(db, project_id)

    # Query total reviews and average rating
    stats_stmt = (
        select(
            func.count(Review.id).label("total_reviews"),
            func.avg(Review.rating).label("avg_rating"),
        )
        .where(Review.project_id == project_id)
    )
    total_reviews, avg_rating = db.execute(stats_stmt).one()
    total_reviews = total_reviews or 0
    average_rating = round(float(avg_rating), 2) if avg_rating is not None else None

    # Query counts grouped by rating (1 through 5)
    distribution_stmt = (
        select(Review.rating, func.count(Review.id))
        .where(Review.project_id == project_id)
        .group_by(Review.rating)
    )
    raw_distribution = dict(db.execute(distribution_stmt).all())

    # Ensure all ratings 1 to 5 are populated
    rating_counts: Dict[int, int] = {rating: raw_distribution.get(rating, 0) for rating in range(1, 6)}

    return ProjectAnalyticsSummary(
        project_id=project.id,
        project_name=project.name,
        total_reviews=total_reviews,
        average_rating=average_rating,
        rating_counts=rating_counts,
    )
