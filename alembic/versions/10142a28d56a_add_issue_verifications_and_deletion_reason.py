"""add issue_verifications and deletion_reason

Revision ID: 10142a28d56a
Revises: 6177d08b0a33
Create Date: 2026-09-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '10142a28d56a'
down_revision: Union[str, Sequence[str], None] = '6177d08b0a33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add deletion_reason to issues
    op.add_column('issues', sa.Column('deletion_reason', sa.String(), nullable=True))

    # 2. Create issue_verifications table
    op.create_table(
        'issue_verifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('issue_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('citizen_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('response', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['citizen_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('issue_id', 'citizen_id', name='uq_issue_verification_citizen_issue'),
    )
    op.create_index('ix_issue_verifications_citizen_id', 'issue_verifications', ['citizen_id'], unique=False)
    op.create_index('ix_issue_verifications_issue_id', 'issue_verifications', ['issue_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_issue_verifications_issue_id', table_name='issue_verifications')
    op.drop_index('ix_issue_verifications_citizen_id', table_name='issue_verifications')
    op.drop_table('issue_verifications')
    op.drop_column('issues', 'deletion_reason')
