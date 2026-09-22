"""add points and point transaction ledger
Revision ID: rewards20260922
Revises: 6177d08b0a33
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision: str = "rewards20260922"
down_revision: Union[str, Sequence[str], None] = "6177d08b0a33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
def upgrade() -> None:
    op.add_column("profiles", sa.Column("points", sa.Integer(), nullable=False, server_default="0"))
    op.create_table("point_transactions", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("points", sa.Integer(), nullable=False), sa.Column("reason", sa.Text(), nullable=False), sa.Column("issue_id", postgresql.UUID(as_uuid=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["user_id"], ["profiles.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_point_transactions_user_id", "point_transactions", ["user_id"])
    op.create_index("ix_point_transactions_issue_id", "point_transactions", ["issue_id"])
def downgrade() -> None:
    op.drop_index("ix_point_transactions_issue_id", table_name="point_transactions")
    op.drop_index("ix_point_transactions_user_id", table_name="point_transactions")
    op.drop_table("point_transactions")
    op.drop_column("profiles", "points")
