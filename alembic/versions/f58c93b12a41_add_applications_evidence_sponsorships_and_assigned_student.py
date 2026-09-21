"""add_applications_evidence_sponsorships_and_assigned_student

Revision ID: f58c93b12a41
Revises: d800b2d30db3
Create Date: 2026-09-21 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f58c93b12a41'
down_revision: Union[str, Sequence[str], None] = 'd800b2d30db3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add assigned_student_id to issues
    op.add_column(
        'issues',
        sa.Column('assigned_student_id', sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        'fk_issues_assigned_student_id_profiles',
        'issues',
        'profiles',
        ['assigned_student_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_issues_assigned_student_id', 'issues', ['assigned_student_id'])

    # 2. Create applications table
    op.create_table(
        'applications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('issue_id', sa.UUID(), nullable=False),
        sa.Column('student_id', sa.UUID(), nullable=False),
        sa.Column('proposal', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('issue_id', 'student_id', name='uq_applications_issue_student'),
    )
    op.create_index('ix_applications_issue_id', 'applications', ['issue_id'])
    op.create_index('ix_applications_student_id', 'applications', ['student_id'])
    op.create_index('ix_applications_status', 'applications', ['status'])

    # 3. Create evidence table
    op.create_table(
        'evidence',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('issue_id', sa.UUID(), nullable=False),
        sa.Column('student_id', sa.UUID(), nullable=False),
        sa.Column('media_url', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('evidence_type', sa.Text(), nullable=False, server_default='PROGRESS'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_evidence_issue_id', 'evidence', ['issue_id'])
    op.create_index('ix_evidence_student_id', 'evidence', ['student_id'])
    op.create_index('ix_evidence_evidence_type', 'evidence', ['evidence_type'])

    # 4. Create sponsorships table
    op.create_table(
        'sponsorships',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('issue_id', sa.UUID(), nullable=False),
        sa.Column('industrialist_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='PLEDGED'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['industrialist_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sponsorships_issue_id', 'sponsorships', ['issue_id'])
    op.create_index('ix_sponsorships_industrialist_id', 'sponsorships', ['industrialist_id'])
    op.create_index('ix_sponsorships_status', 'sponsorships', ['status'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_sponsorships_status', table_name='sponsorships')
    op.drop_index('ix_sponsorships_industrialist_id', table_name='sponsorships')
    op.drop_index('ix_sponsorships_issue_id', table_name='sponsorships')
    op.drop_table('sponsorships')

    op.drop_index('ix_evidence_evidence_type', table_name='evidence')
    op.drop_index('ix_evidence_student_id', table_name='evidence')
    op.drop_index('ix_evidence_issue_id', table_name='evidence')
    op.drop_table('evidence')

    op.drop_index('ix_applications_status', table_name='applications')
    op.drop_index('ix_applications_student_id', table_name='applications')
    op.drop_index('ix_applications_issue_id', table_name='applications')
    op.drop_table('applications')

    op.drop_index('ix_issues_assigned_student_id', table_name='issues')
    op.drop_constraint('fk_issues_assigned_student_id_profiles', 'issues', type_='foreignkey')
    op.drop_column('issues', 'assigned_student_id')
