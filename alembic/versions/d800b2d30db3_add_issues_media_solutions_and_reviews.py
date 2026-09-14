"""add_issues_media_solutions_and_reviews

Revision ID: d800b2d30db3
Revises: ba3667551077
Create Date: 2026-09-13 18:45:45.865966

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd800b2d30db3'
down_revision: Union[str, Sequence[str], None] = 'ba3667551077'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'issues',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('reporter_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.Text(), nullable=True),
        sa.Column('category_confidence', sa.Float(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='REPORTED'),
        sa.Column('priority', sa.Text(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['reporter_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_issues_reporter_id', 'issues', ['reporter_id'])
    op.create_index('ix_issues_status', 'issues', ['status'])
    op.create_index('ix_issues_category', 'issues', ['category'])

    op.create_table(
        'issue_media',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('issue_id', sa.UUID(), nullable=False),
        sa.Column('media_url', sa.Text(), nullable=False),
        sa.Column('media_type', sa.Text(), nullable=False, server_default='image'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_issue_media_issue_id', 'issue_media', ['issue_id'])

    op.create_table(
        'solutions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('issue_id', sa.UUID(), nullable=False),
        sa.Column('student_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('pdf_url', sa.Text(), nullable=True),
        sa.Column('prototype_url', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='SUBMITTED'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_solutions_issue_id', 'solutions', ['issue_id'])
    op.create_index('ix_solutions_student_id', 'solutions', ['student_id'])
    op.create_index('ix_solutions_status', 'solutions', ['status'])

    op.create_table(
        'solution_reviews',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('solution_id', sa.UUID(), nullable=False),
        sa.Column('reviewer_id', sa.UUID(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['solution_id'], ['solutions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_solution_reviews_solution_id', 'solution_reviews', ['solution_id'])
    op.create_index('ix_solution_reviews_reviewer_id', 'solution_reviews', ['reviewer_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_solution_reviews_reviewer_id', table_name='solution_reviews')
    op.drop_index('ix_solution_reviews_solution_id', table_name='solution_reviews')
    op.drop_table('solution_reviews')

    op.drop_index('ix_solutions_status', table_name='solutions')
    op.drop_index('ix_solutions_student_id', table_name='solutions')
    op.drop_index('ix_solutions_issue_id', table_name='solutions')
    op.drop_table('solutions')

    op.drop_index('ix_issue_media_issue_id', table_name='issue_media')
    op.drop_table('issue_media')

    op.drop_index('ix_issues_category', table_name='issues')
    op.drop_index('ix_issues_status', table_name='issues')
    op.drop_index('ix_issues_reporter_id', table_name='issues')
    op.drop_table('issues')
