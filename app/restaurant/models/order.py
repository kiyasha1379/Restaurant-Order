"""Orders: the order, its lines, the options chosen on a line and the status history.

Every name and price on an order is a snapshot taken when the order is placed,
so changing the menu later never rewrites old orders (technical plan, section 4).
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from restaurant.constants import FulfillmentType, OrderStatus, PaymentMethod, PaymentStatus
from restaurant.extensions import db
from restaurant.models.access import User
from restaurant.models.columns import enum_type
from restaurant.models.mixins import SnapshotNameMixin, TimestampMixin
from restaurant.timeutils import now_tehran


class Order(TimestampMixin, db.Model):
    """One order. `public_token` is the unguessable part of the tracking address."""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "subtotal >= 0 AND delivery_fee >= 0 AND total >= 0", name="amounts_not_negative"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_token: Mapped[str] = mapped_column(String(32), unique=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    language_code: Mapped[str] = mapped_column(String(5))
    customer_name: Mapped[str] = mapped_column(String(120))
    customer_phone: Mapped[str] = mapped_column(String(20))
    fulfillment: Mapped[FulfillmentType] = mapped_column(enum_type(FulfillmentType))
    delivery_address: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")
    payment_method: Mapped[PaymentMethod] = mapped_column(enum_type(PaymentMethod))
    status: Mapped[OrderStatus] = mapped_column(enum_type(OrderStatus), default=OrderStatus.PLACED)
    subtotal: Mapped[int] = mapped_column(default=0)
    delivery_fee: Mapped[int] = mapped_column(default=0)
    total: Mapped[int] = mapped_column(default=0)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id"
    )
    status_log: Mapped[list["OrderStatusLog"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderStatusLog.id"
    )
    payments: Mapped[list["Payment"]] = relationship(  # noqa: F821
        back_populates="order", cascade="all, delete-orphan", order_by="Payment.id"
    )

    @property
    def number(self) -> int:
        """The order number shown to people (the row id)."""
        return self.id

    @property
    def latest_payment(self) -> "Payment | None":  # noqa: F821
        """The newest payment attempt, or None for an order from before payments were stored."""
        return self.payments[-1] if self.payments else None

    @property
    def is_paid(self) -> bool:
        """Return True once any payment of the order has been verified."""
        return any(payment.status is PaymentStatus.PAID for payment in self.payments)


class OrderItem(SnapshotNameMixin, db.Model):
    """One line of an order. `dish_id` is kept only as a link; the snapshot is what counts."""

    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0 AND line_total >= 0", name="amounts_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    dish_id: Mapped[int | None] = mapped_column(ForeignKey("dishes.id", ondelete="SET NULL"))
    # Set on a custom build, so a past order can be ordered again.
    builder_id: Mapped[int | None] = mapped_column(ForeignKey("builders.id", ondelete="SET NULL"))
    name_fa: Mapped[str] = mapped_column(String(160))
    name_en: Mapped[str] = mapped_column(String(160), default="")
    unit_price: Mapped[int]
    quantity: Mapped[int]
    line_total: Mapped[int]

    order: Mapped[Order] = relationship(back_populates="items")
    options: Mapped[list["OrderItemOption"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="OrderItemOption.order_index"
    )


class OrderItemOption(SnapshotNameMixin, db.Model):
    """One option chosen on a builder line. `order_index` keeps sandwich layer order."""

    __tablename__ = "order_item_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="CASCADE"))
    order_index: Mapped[int] = mapped_column(default=0)
    option_id: Mapped[int | None] = mapped_column(
        ForeignKey("builder_options.id", ondelete="SET NULL")
    )
    name_fa: Mapped[str] = mapped_column(String(160))
    name_en: Mapped[str] = mapped_column(String(160), default="")
    # The step the option belongs to ("Size", "Sauce"...), so the kitchen reads "Size: Large".
    group_fa: Mapped[str] = mapped_column(String(160), default="")
    group_en: Mapped[str] = mapped_column(String(160), default="")
    price: Mapped[int] = mapped_column(default=0)

    item: Mapped[OrderItem] = relationship(back_populates="options")


class OrderStatusLog(db.Model):
    """One move of an order from a status to the next, with who made it and when."""

    __tablename__ = "order_status_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    from_status: Mapped[OrderStatus | None] = mapped_column(enum_type(OrderStatus))
    to_status: Mapped[OrderStatus] = mapped_column(enum_type(OrderStatus))
    changed_at: Mapped[datetime] = mapped_column(default=now_tehran)
    changed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    order: Mapped[Order] = relationship(back_populates="status_log")
    changed_by: Mapped[User | None] = relationship()
