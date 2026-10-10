from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Review(Base):
    """
    Review model representing individual consumer feedback for a project.
    Rating is constrained between 1 and 5 inclusive.
    Foreign key references projects.id with RESTRICT on delete to prevent accidental orphaned data.
    """
    __tablename__ = "reviews"

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
        Index("ix_reviews_project_id_created_at", "project_id", "created_at"),
        Index("ix_reviews_rating", "rating"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    customer_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship back to Project
    project: Mapped["Project"] = relationship("Project", back_populates="reviews")

    def __repr__(self) -> str:
        return f"<Review(id={self.id}, project_id={self.project_id}, rating={self.rating})>"
