"""Add is_active + datetime fields to Checkin

Revision ID: e86d7e4081cd
Revises: 
Create Date: 2025-07-15 11:08:59.169790
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e86d7e4081cd'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('checkin', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=True))
        batch_op.alter_column('user',
            existing_type=sa.VARCHAR(length=100),
            nullable=False)
        batch_op.alter_column('checkin_time',
            existing_type=sa.VARCHAR(length=50),
            type_=sa.DateTime(),
            existing_nullable=True,
            postgresql_using="checkin_time::timestamp")
        batch_op.alter_column('checkout_time',
            existing_type=sa.VARCHAR(length=50),
            type_=sa.DateTime(),
            existing_nullable=True,
            postgresql_using="checkout_time::timestamp")


def downgrade():
    with op.batch_alter_table('checkin', schema=None) as batch_op:
        batch_op.alter_column('checkout_time',
            existing_type=sa.DateTime(),
            type_=sa.VARCHAR(length=50),
            existing_nullable=True)
        batch_op.alter_column('checkin_time',
            existing_type=sa.DateTime(),
            type_=sa.VARCHAR(length=50),
            existing_nullable=True)
        batch_op.alter_column('user',
            existing_type=sa.VARCHAR(length=100),
            nullable=True)
        batch_op.drop_column('is_active')
