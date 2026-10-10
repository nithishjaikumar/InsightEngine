from typing import Generic, List, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Query parameters for limit-offset pagination."""
    limit: int = Field(default=20, ge=1, le=100, description="Number of items to return (1-100)")
    offset: int = Field(default=0, ge=0, description="Offset index (>= 0)")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard container for paginated list endpoints."""
    total: int = Field(..., description="Total number of items matching criteria")
    limit: int = Field(..., description="Number of items requested")
    offset: int = Field(..., description="Current offset")
    items: List[T] = Field(..., description="List of items for this page")


class ErrorDetail(BaseModel):
    """Structured error detail representation."""
    detail: str = Field(..., description="Human-readable error explanation")
