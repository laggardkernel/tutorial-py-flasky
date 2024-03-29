"""confirmed field support in User model

Revision ID: 43aacde2ce1c
Revises: a2b38779912f
Create Date: 2017-10-19 15:25:42.460341

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '43aacde2ce1c'
down_revision = 'a2b38779912f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('confirmed', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'confirmed')
    # ### end Alembic commands ###
