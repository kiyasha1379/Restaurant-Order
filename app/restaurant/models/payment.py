"""Payments: one row per payment attempt of an order.

Pay on site and online share one row shape (technical plan, section 4). An online
order gets a new row for every attempt, so a failed try stays visible next to the next one.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from restaurant.constants import PaymentMethod, PaymentStatus
from restaurant.extensions import db
from restaurant.models.columns import enum_type
from restaurant.models.mixins import TimestampMixin

# Transaction ids of the test gateway start with this, so staff can tell them from real ones.
MOCK_TRANSACTION_PREFIX = "MOCK-"
MOCK_GATEWAY_NAME = "mock"


class Payment(TimestampMixin, db.Model):
    """One attempt to pay an order. `authority` is the gateway's reference for the attempt."""

    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount >= 0", name="amount_not_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    method: Mapped[PaymentMethod] = mapped_column(enum_type(PaymentMethod))
    # The gateway that handled it ("mock"); empty for pay on site.
    gateway: Mapped[str] = mapped_column(String(30), default="")
    status: Mapped[PaymentStatus] = mapped_column(
        enum_type(PaymentStatus), default=PaymentStatus.PENDING
    )
    amount: Mapped[int]
    authority: Mapped[str | None] = mapped_column(String(64), unique=True)
    transaction_id: Mapped[str] = mapped_column(String(64), default="")
    paid_at: Mapped[datetime | None]

    order: Mapped["Order"] = relationship(back_populates="payments")  # noqa: F821

    @property
    def is_test(self) -> bool:
        """Return True for a payment made through the test gateway (no money moved)."""
        return self.gateway == MOCK_GATEWAY_NAME or self.transaction_id.startswith(
            MOCK_TRANSACTION_PREFIX
        )
