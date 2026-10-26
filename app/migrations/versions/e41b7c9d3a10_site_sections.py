"""site sections

Revision ID: e41b7c9d3a10
Revises: d2a58ea71365
Create Date: 2026-10-26 16:05:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e41b7c9d3a10"
down_revision = "d2a58ea71365"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "site_sections",
        sa.Column("key", sa.String(length=30), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_visible", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_site_sections")),
    )


def downgrade():
    op.drop_table("site_sections")
