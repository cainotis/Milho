"""fix data type

Revision ID: 2083d37665e0
Revises: 587bf427336d
Create Date: 2021-10-11 03:20:47.651190

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2083d37665e0'
down_revision = '587bf427336d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('server') as batch_op:
        batch_op.drop_column('guild_id')
        batch_op.drop_column('chat')
        batch_op.add_column(sa.Column('guild_id', sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column('channel_id', sa.Integer(), nullable=True))


def downgrade():
    pass