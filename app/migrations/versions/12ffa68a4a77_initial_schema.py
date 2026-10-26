"""initial schema

Revision ID: 12ffa68a4a77
Revises:
Create Date: 2026-10-26 09:06:03.514900

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "12ffa68a4a77"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "backgrounds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=60), nullable=False),
        sa.Column("video_path", sa.String(length=255), nullable=True),
        sa.Column("poster_path", sa.String(length=255), nullable=True),
        sa.Column("dim", sa.Double(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "mobile_mode",
            sa.Enum("poster_only", "video", name="mobilebackgroundmode", native_enum=False),
            nullable=False,
        ),
        sa.CheckConstraint(
            "dim >= 0 AND dim <= 1", name=op.f("ck_backgrounds_dim_between_0_and_1")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_backgrounds")),
        sa.UniqueConstraint("key", name=op.f("uq_backgrounds_key")),
    )
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_visible", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint("slug", name=op.f("uq_categories_slug")),
    )
    op.create_table(
        "languages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=5), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column(
            "direction",
            sa.Enum("rtl", "ltr", name="textdirection", native_enum=False),
            nullable=False,
        ),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.CheckConstraint("code IN ('fa', 'en')", name=op.f("ck_languages_supported_code")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_languages")),
        sa.UniqueConstraint("code", name=op.f("uq_languages_code")),
    )
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_permissions")),
        sa.UniqueConstraint("key", name=op.f("uq_permissions_key")),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("key", name=op.f("uq_roles_key")),
    )
    op.create_table(
        "settings",
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_settings")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        sa.UniqueConstraint("phone", name=op.f("uq_users_phone")),
    )
    op.create_table(
        "category_translations",
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("language_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_category_translations_category_id_categories"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["language_id"],
            ["languages.id"],
            name=op.f("fk_category_translations_language_id_languages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "category_id", "language_id", name=op.f("pk_category_translations")
        ),
    )
    op.create_table(
        "dishes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("base_price", sa.Integer(), nullable=False),
        sa.Column("is_in_stock", sa.Boolean(), nullable=False),
        sa.Column("is_chefs_pick", sa.Boolean(), nullable=False),
        sa.Column("is_visible", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("base_price >= 0", name=op.f("ck_dishes_base_price_not_negative")),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_dishes_category_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dishes")),
    )
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.Column(
            "access_level",
            sa.Enum("none", "view", "edit", name="accesslevel", native_enum=False),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            name=op.f("fk_role_permissions_permission_id_permissions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_role_permissions_role_id_roles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role_permissions")),
        sa.UniqueConstraint("role_id", "permission_id", name=op.f("uq_role_permissions_role_id")),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name=op.f("fk_user_roles_role_id_roles"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_roles_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id", name=op.f("pk_user_roles")),
    )
    op.create_table(
        "dish_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dish_id", sa.Integer(), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dish_id"],
            ["dishes.id"],
            name=op.f("fk_dish_images_dish_id_dishes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dish_images")),
    )
    op.create_table(
        "dish_translations",
        sa.Column("dish_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("language_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dish_id"],
            ["dishes.id"],
            name=op.f("fk_dish_translations_dish_id_dishes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["language_id"],
            ["languages.id"],
            name=op.f("fk_dish_translations_language_id_languages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("dish_id", "language_id", name=op.f("pk_dish_translations")),
    )

    # The site always has exactly these two languages (technical plan, section 7),
    # so they are part of the schema, not sample data.
    languages = sa.table(
        "languages",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("direction", sa.String),
        sa.column("is_default", sa.Boolean),
        sa.column("is_enabled", sa.Boolean),
    )
    op.bulk_insert(
        languages,
        [
            {
                "code": "fa",
                "name": "فارسی",
                "direction": "rtl",
                "is_default": True,
                "is_enabled": True,
            },
            {
                "code": "en",
                "name": "English",
                "direction": "ltr",
                "is_default": False,
                "is_enabled": True,
            },
        ],
    )


def downgrade():
    op.drop_table("dish_translations")
    op.drop_table("dish_images")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("dishes")
    op.drop_table("category_translations")
    op.drop_table("users")
    op.drop_table("settings")
    op.drop_table("roles")
    op.drop_table("permissions")
    op.drop_table("languages")
    op.drop_table("categories")
    op.drop_table("backgrounds")
