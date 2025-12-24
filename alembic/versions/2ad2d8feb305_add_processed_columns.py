"""Add is_processed, processed_by, processed_at columns

Revision ID: 2ad2d8feb305
Revises: 317d5f6ddfb6
Create Date: 2025-01-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2ad2d8feb305'
down_revision: Union[str, Sequence[str], None] = '317d5f6ddfb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add is_processed column with default False
    op.add_column('analysis_results', sa.Column('is_processed', sa.Boolean(), server_default='false', nullable=False))
    # Add processed_by column (nullable, stores user ID or email)
    op.add_column('analysis_results', sa.Column('processed_by', sa.String(255), nullable=True))
    # Add processed_at column (nullable timestamp)
    op.add_column('analysis_results', sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('analysis_results', 'processed_at')
    op.drop_column('analysis_results', 'processed_by')
    op.drop_column('analysis_results', 'is_processed')
