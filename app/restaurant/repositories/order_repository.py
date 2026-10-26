"""Queries for orders."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, or_, select
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
