"""orders

Revision ID: 3e8c09f77899
Revises: 63afcd125f01
Create Date: 2026-10-26 09:44:55.139848

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "3e8c09f77899"
down_revision = "63afcd125f01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_token", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("language_code", sa.String(length=5), nullable=False),
        sa.Column("customer_name", sa.String(length=120), nullable=False),
        sa.Column("customer_phone", sa.String(length=20), nullable=False),
        sa.Column(
            "fulfillment",
            sa.Enum("takeaway", "delivery", name="fulfillmenttype", native_enum=False),
            nullable=False,
        ),
        sa.Column("delivery_address", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column(
            "payment_method",
            sa.Enum("cash_on_site", "online", name="paymentmethod", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "placed",
                "preparing",
                "ready",
                "out_for_delivery",
                "completed",
                "cancelled",
                name="orderstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("subtotal", sa.Integer(), nullable=False),
        sa.Column("delivery_fee", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "subtotal >= 0 AND delivery_fee >= 0 AND total >= 0",
            name=op.f("ck_orders_amounts_not_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_orders_user_id_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
        sa.UniqueConstraint("public_token", name=op.f("uq_orders_public_token")),
    )
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("dish_id", sa.Integer(), nullable=True),
        sa.Column("name_fa", sa.String(length=160), nullable=False),
        sa.Column("name_en", sa.String(length=160), nullable=False),
        sa.Column("unit_price", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("line_total", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_order_items_quantity_positive")),
        sa.CheckConstraint(
            "unit_price >= 0 AND line_total >= 0", name=op.f("ck_order_items_amounts_not_negative")
        ),
        sa.ForeignKeyConstraint(
            ["dish_id"],
            ["dishes.id"],
            name=op.f("fk_order_items_dish_id_dishes"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_order_items_order_id_orders"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_items")),
    )
    op.create_table(
        "order_status_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column(
            "from_status",
            sa.Enum(
                "placed",
                "preparing",
                "ready",
                "out_for_delivery",
                "completed",
                "cancelled",
                name="orderstatus",
                native_enum=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "to_status",
            sa.Enum(
                "placed",
                "preparing",
                "ready",
                "out_for_delivery",
                "completed",
                "cancelled",
                name="orderstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"],
            ["users.id"],
            name=op.f("fk_order_status_log_changed_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_order_status_log_order_id_orders"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_status_log")),
    )
    op.create_table(
        "order_item_options",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_item_id", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("name_fa", sa.String(length=160), nullable=False),
        sa.Column("name_en", sa.String(length=160), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_item_id"],
            ["order_items.id"],
            name=op.f("fk_order_item_options_order_item_id_order_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_item_options")),
    )


def downgrade():
    op.drop_table("order_item_options")
    op.drop_table("order_status_log")
    op.drop_table("order_items")
    op.drop_table("orders")
