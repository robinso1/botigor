"""add_last_lead_at_to_users

Revision ID: 49b2fbc00fe1
Revises: 
Create Date: 2025-02-26 17:47:26.439410

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49b2fbc00fe1'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
