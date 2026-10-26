"""Queries for orders."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import joinedload, selectinload

from restaurant.constants import FulfillmentType, OrderStatus
from restaurant.models import Order, OrderItem, OrderStatusLog
from restaurant.repositories.base import BaseRepository


@dataclass(frozen=True)
class OrderFilter:
    """What the order list is narrowed to. `None` means "any"."""

    status: OrderStatus | None = None
    fulfillment: FulfillmentType | None = None
    text: str = ""


@dataclass(frozen=True)
class CustomerOrderStats:
    """What one customer has ordered so far (cancelled and unpaid online orders are not counted)."""

    order_count: int
    total_spent: int
    last_order_at: datetime


class OrderRepository(BaseRepository[Order]):
    """Reads and stores orders with their lines and status history."""

    model = Order

    def get_by_token(self, public_token: str) -> Order | None:
        """Return the order behind a tracking address, or None."""
        statement = (
            select(Order)
            .where(Order.public_token == public_token)
            .options(selectinload(Order.items), selectinload(Order.status_log))
        )
        return self._session.scalar(statement)

    def count_by_status(self) -> dict[OrderStatus, int]:
        """Return how many orders are in each status (statuses with none are left out)."""
        rows = self._session.execute(
            select(Order.status, func.count(Order.id)).group_by(Order.status)
        )
        return {status: count for status, count in rows}

    def list_between(self, start: datetime, end: datetime) -> list[Order]:
        """Return the orders placed from `start` (inclusive) to `end` (exclusive), oldest first."""
        statement = (
            select(Order)
            .where(Order.created_at >= start, Order.created_at < end)
            .order_by(Order.created_at, Order.id)
        )
        return list(self._session.scalars(statement))

    def list_with_statuses(
        self, statuses: list[OrderStatus], since: datetime | None = None
    ) -> list[Order]:
        """Return orders in these statuses, oldest first; `since` drops older ones."""
        statement = (
            select(Order)
            .where(Order.status.in_(statuses))
            .options(*self._detail_options())
            .order_by(Order.created_at, Order.id)
        )
        if since is not None:
            statement = statement.where(Order.created_at >= since)
        return list(self._session.scalars(statement))

    def search(self, order_filter: OrderFilter, offset: int, limit: int) -> tuple[list[Order], int]:
        """Return one page of orders (newest first) and the total number that match."""
        conditions = []
        if order_filter.status is not None:
            conditions.append(Order.status == order_filter.status)
        if order_filter.fulfillment is not None:
            conditions.append(Order.fulfillment == order_filter.fulfillment)
        text = order_filter.text.strip()
        if text:
            like = f"%{text}%"
            matches = [Order.customer_name.like(like), Order.customer_phone.like(like)]
            if text.isdecimal():
                matches.append(Order.id == int(text))
            conditions.append(or_(*matches))
        total = self._session.scalar(select(func.count(Order.id)).where(*conditions)) or 0
        statement = (
            select(Order)
            .where(*conditions)
            .options(selectinload(Order.items))
            .order_by(Order.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.scalars(statement)), total

    def list_for_user(self, user_id: int, offset: int, limit: int) -> tuple[list[Order], int]:
        """Return one page of a customer's orders (newest first) and how many they have."""
        total = (
            self._session.scalar(select(func.count(Order.id)).where(Order.user_id == user_id)) or 0
        )
        statement = (
            select(Order)
            .where(Order.user_id == user_id)
            .options(selectinload(Order.items))
            .order_by(Order.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.scalars(statement)), total

    def get_for_user(self, user_id: int, public_token: str) -> Order | None:
        """Return the order behind this token if it belongs to the customer, else None."""
        statement = (
            select(Order)
            .where(Order.public_token == public_token, Order.user_id == user_id)
            .options(selectinload(Order.items).selectinload(OrderItem.options))
        )
        return self._session.scalar(statement)

    def stats_for_users(self, user_ids: list[int]) -> dict[int, "CustomerOrderStats"]:
        """Return how many orders each customer placed, what they spent and their last order."""
        if not user_ids:
            return {}
        rows = self._session.execute(
            select(
                Order.user_id,
                func.count(Order.id),
                func.coalesce(func.sum(Order.total), 0),
                func.max(Order.created_at),
            )
            .where(
                Order.user_id.in_(user_ids),
                Order.status.not_in([OrderStatus.CANCELLED, OrderStatus.AWAITING_PAYMENT]),
            )
            .group_by(Order.user_id)
        )
        return {
            user_id: CustomerOrderStats(count, spent, last_at)
            for user_id, count, spent, last_at in rows
        }

    def claim_guest_orders(self, phone: str, user_id: int) -> int:
        """Attach the guest orders placed with this phone number to the customer's account."""
        result = self._session.execute(
            update(Order)
            .where(Order.customer_phone == phone, Order.user_id.is_(None))
            .values(user_id=user_id)
        )
        return result.rowcount or 0

    def get_detail(self, order_id: int) -> Order | None:
        """Return one order with its lines, options and status history loaded."""
        statement = select(Order).where(Order.id == order_id).options(*self._detail_options())
        return self._session.scalar(statement)

    def change_marker(self) -> str:
        """Return a short text that changes whenever an order is placed or changes status."""
        count = self._session.scalar(select(func.count(Order.id))) or 0
        last_log = self._session.scalar(select(func.max(OrderStatusLog.id))) or 0
        return f"{count}-{last_log}"

    @staticmethod
    def _detail_options() -> tuple:
        """Loader options that bring in lines, chosen options and the status history."""
        return (
            selectinload(Order.items).selectinload(OrderItem.options),
            selectinload(Order.status_log).options(joinedload(OrderStatusLog.changed_by)),
        )
