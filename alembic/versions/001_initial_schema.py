"""Initial schema: projects and reviews

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)
    op.create_index(op.f('ix_projects_name'), 'projects', ['name'], unique=True)

    # 2. Create reviews table
    op.create_table(
        'reviews',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('customer_name', sa.String(length=100), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('review_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='ck_review_rating_range'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reviews_id'), 'reviews', ['id'], unique=False)
    op.create_index(op.f('ix_reviews_project_id'), 'reviews', ['project_id'], unique=False)
    op.create_index(op.f('ix_reviews_rating'), 'reviews', ['rating'], unique=False)
    op.create_index(op.f('ix_reviews_created_at'), 'reviews', ['created_at'], unique=False)
    op.create_index('ix_reviews_project_id_created_at', 'reviews', ['project_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_reviews_project_id_created_at', table_name='reviews')
    op.drop_index(op.f('ix_reviews_created_at'), table_name='reviews')
    op.drop_index(op.f('ix_reviews_rating'), table_name='reviews')
    op.drop_index(op.f('ix_reviews_project_id'), table_name='reviews')
    op.drop_index(op.f('ix_reviews_id'), table_name='reviews')
    op.drop_table('reviews')

    op.drop_index(op.f('ix_projects_name'), table_name='projects')
    op.drop_index(op.f('ix_projects_id'), table_name='projects')
    op.drop_table('projects')
