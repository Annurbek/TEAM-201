"""email changed to username

Revision ID: 99596752080c
Revises: 255ae92f2343
Create Date: 2026-05-20 22:50:22.793949
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



revision: str = '99596752080c'
down_revision: Union[str, None] = '255ae92f2343'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add username column as nullable to allow safe data migration
    op.add_column('users', sa.Column('username', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('last_login', sa.DateTime(), nullable=True))

    # Populate username from existing email values for legacy rows
    op.execute("UPDATE users SET username = email")

    # Enforce uniqueness and non-null after population
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.alter_column('users', 'username', nullable=False)

    # Remove legacy email column
    op.drop_column('users', 'email')


def downgrade() -> None:
    # Recreate email as nullable for safe rollback
    op.add_column('users', sa.Column('email', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.execute("UPDATE users SET email = username")

    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.alter_column('users', 'email', nullable=False)

    op.drop_column('users', 'last_login')
    op.drop_column('users', 'username')
