from typing import Annotated
from fastapi import Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.common import PaginationParams

# Type alias for database session dependency
DatabaseSession = Annotated[Session, Depends(get_db)]


def get_pagination_params(
    limit: int = Query(default=20, ge=1, le=100, description="Items per page (1-100)"),
    offset: int = Query(default=0, ge=0, description="Page offset (>= 0)"),
) -> PaginationParams:
    """Dependency for limit-offset pagination query parameters."""
    return PaginationParams(limit=limit, offset=offset)


PaginationDep = Annotated[PaginationParams, Depends(get_pagination_params)]
