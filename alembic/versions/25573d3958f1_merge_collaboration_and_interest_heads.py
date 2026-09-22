"""merge collaboration and interest heads

Revision ID: 25573d3958f1
Revises: 3d6d937c0376, collaboration20260922
Create Date: 2026-09-22 23:23:36.371999

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '25573d3958f1'
down_revision: Union[str, Sequence[str], None] = ('3d6d937c0376', 'collaboration20260922')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
