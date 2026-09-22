"""add collaborations and selected application status

Revision ID: collaboration20260922
Revises: 6177d08b0a33

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "collaboration20260922"
down_revision: Union[str, Sequence[str], None] = ("6177d08b0a33", "rewards20260922")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collaborations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("issue_id", sa.UUID(), nullable=False),
        sa.Column("application_id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("industrialist_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="ACTIVE"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["industrialist_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", name="uq_collaborations_application"),
    )
    op.create_index("ix_collaborations_issue_id", "collaborations", ["issue_id"])
    op.create_index("ix_collaborations_application_id", "collaborations", ["application_id"])
    op.create_index("ix_collaborations_student_id", "collaborations", ["student_id"])
    op.create_index("ix_collaborations_industrialist_id", "collaborations", ["industrialist_id"])
    op.create_index("ix_collaborations_status", "collaborations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_collaborations_status", table_name="collaborations")
    op.drop_index("ix_collaborations_industrialist_id", table_name="collaborations")
    op.drop_index("ix_collaborations_student_id", table_name="collaborations")
    op.drop_index("ix_collaborations_application_id", table_name="collaborations")
    op.drop_index("ix_collaborations_issue_id", table_name="collaborations")
    op.drop_table("collaborations")
