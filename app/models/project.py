from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Project(Base):
    """
    Project model representing a product or service under analysis.
    Maintains a 1-to-many relationship with Review instances.
    """
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # One-to-many relationship with reviews (restrictive deletion; no cascade delete)
    reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="project",
        passive_deletes="all",
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}')>"
