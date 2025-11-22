"""add uuid

Revision ID: 757d9eed2924
Revises: 
Create Date: 2025-11-20 20:20:09.982155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '757d9eed2924'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('analysis_results', sa.Column('uuid', sa.UUID(), nullable=True))

    connection = op.get_bind()
    connection.execute(sa.text("UPDATE analysis_results SET uuid = gen_random_uuid() WHERE uuid IS NULL"))

    # 3. Alter the column to be non-nullable
    op.alter_column('analysis_results', 'uuid', nullable=False)

def downgrade() -> None:
    op.drop_column('analysis_results', 'uuid')
