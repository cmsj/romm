"""empty message

Revision ID: 0017_tgdb_metadata
Revises: 0016_user_last_login_active
Create Date: 2024-04-28 10:00:34.261426

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '0017_tgdb_metadata'
down_revision = '0016_user_last_login_active'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('platforms', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tgdb_id', sa.Integer(), nullable=True))

    with op.batch_alter_table('roms', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tgdb_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('tgdb_metadata', mysql.JSON(), nullable=True))

    with op.batch_alter_table("roms", schema=None) as batch_op:
        batch_op.execute("update roms set tgdb_metadata = '\\{\\}'")

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('roms', schema=None) as batch_op:
        batch_op.drop_column('tgdb_metadata')
        batch_op.drop_column('tgdb_id')

    with op.batch_alter_table('platforms', schema=None) as batch_op:
        batch_op.drop_column('tgdb_id')

    # ### end Alembic commands ###