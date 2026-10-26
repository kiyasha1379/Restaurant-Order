"""ui strings

Revision ID: 9cacabae2fb7
Revises: 12ffa68a4a77
Create Date: 2026-10-26 09:29:13.288257

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9cacabae2fb7"
down_revision = "12ffa68a4a77"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ui_strings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ui_strings")),
        sa.UniqueConstraint("key", name=op.f("uq_ui_strings_key")),
    )
    op.create_table(
        "ui_string_translations",
        sa.Column("ui_string_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("language_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["language_id"],
            ["languages.id"],
            name=op.f("fk_ui_string_translations_language_id_languages"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ui_string_id"],
            ["ui_strings.id"],
            name=op.f("fk_ui_string_translations_ui_string_id_ui_strings"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "ui_string_id", "language_id", name=op.f("pk_ui_string_translations")
        ),
    )


def downgrade():
    op.drop_table("ui_string_translations")
    op.drop_table("ui_strings")
