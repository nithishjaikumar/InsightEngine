from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReviewBase(BaseModel):
    """Base schema for Review."""
    customer_name: Optional[str] = Field(default=None, max_length=100, description="Optional reviewer name")
    rating: int = Field(..., ge=1, le=5, description="Review rating from 1 to 5")
    review_text: str = Field(..., min_length=1, max_length=5000, description="Customer review text")

    @field_validator("customer_name")
    @classmethod
    def validate_customer_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            return stripped if stripped else None
        return None

    @field_validator("review_text")
    @classmethod
    def validate_review_text(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Review text cannot be empty or whitespace only")
        return stripped


class ReviewCreate(ReviewBase):
    """Schema for creating a review under a project."""
    pass


class ReviewUpdate(BaseModel):
    """Schema for updating a review partially."""
    customer_name: Optional[str] = Field(default=None, max_length=100)
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    review_text: Optional[str] = Field(default=None, min_length=1, max_length=5000)

    @field_validator("customer_name")
    @classmethod
    def validate_customer_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            return stripped if stripped else None
        return None

    @field_validator("review_text")
    @classmethod
    def validate_review_text(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                raise ValueError("Review text cannot be empty or whitespace only")
            return stripped
        return None


class ReviewResponse(BaseModel):
    """Schema for returning review data."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    customer_name: Optional[str] = None
    rating: int
    review_text: str
    created_at: datetime
    updated_at: datetime


class CsvImportRowError(BaseModel):
    """Details of a single row-level CSV validation error."""
    row_number: int = Field(..., description="1-indexed data row number")
    column: Optional[str] = Field(default=None, description="Culprit column name if identifiable")
    error: str = Field(..., description="Explanation of validation failure")


class CsvImportResponse(BaseModel):
    """Summary of CSV import results."""
    project_id: int
    total_rows: int
    imported_records: int
    rejected_records: int
    errors: List[CsvImportRowError] = []
    message: str


class ProjectAnalyticsSummary(BaseModel):
    """Summary analytics for a project's reviews."""
    project_id: int
    project_name: str
    total_reviews: int
    average_rating: Optional[float] = None
    rating_counts: Dict[int, int] = Field(
        ...,
        description="Count of reviews grouped by rating from 1 to 5",
    )
