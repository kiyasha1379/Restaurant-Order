"""Reading orders for the admin panel: the live board, the history list and one order."""

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from restaurant.constants import FulfillmentType, OrderStatus
from restaurant.models import Order
from restaurant.repositories import OrderRepository
from restaurant.repositories.order_repository import OrderFilter
from restaurant.timeutils import now_tehran

PAGE_SIZE = 20


@dataclass(frozen=True)
class BoardColumn:
    """One column of the live board: a key and the statuses shown in it."""

    key: str
    statuses: tuple[OrderStatus, ...]


# Four columns, left to right in the order of an order's life.
BOARD_COLUMNS = (
    BoardColumn("new", (OrderStatus.PLACED,)),
    BoardColumn("preparing", (OrderStatus.PREPARING,)),
    BoardColumn("ready", (OrderStatus.READY, OrderStatus.OUT_FOR_DELIVERY)),
    BoardColumn("done", (OrderStatus.COMPLETED,)),
)


@dataclass(frozen=True)
class BoardData:
    """The board: each column with its orders."""

    columns: list[tuple[BoardColumn, list[Order]]]


@dataclass(frozen=True)
class OrderPage:
    """One page of the order list."""

    orders: list[Order]
    total: int
    page: int
    pages: int


class OrderBoardService:
    """Builds the board and the list from stored orders."""

    def __init__(
        self, order_repository: OrderRepository, clock: Callable[[], datetime] = now_tehran
    ) -> None:
        """Receive the repository and the clock, so tests can fix the time."""
        self._orders = order_repository
        self._clock = clock

    def board(self) -> BoardData:
        """Return the open orders by column; the last column only shows today's finished ones."""
        today = self._clock().replace(hour=0, minute=0, second=0, microsecond=0)
        columns = []
        for column in BOARD_COLUMNS:
            since = today if OrderStatus.COMPLETED in column.statuses else None
            columns.append((column, self._orders.list_with_statuses(list(column.statuses), since)))
        return BoardData(columns)

    def search(
        self,
        status: OrderStatus | None = None,
        fulfillment: FulfillmentType | None = None,
        text: str = "",
        page: int = 1,
    ) -> OrderPage:
        """Return one page of the order history, newest first."""
        page = max(page, 1)
        orders, total = self._orders.search(
            OrderFilter(status, fulfillment, text), (page - 1) * PAGE_SIZE, PAGE_SIZE
        )
        return OrderPage(orders, total, page, max(math.ceil(total / PAGE_SIZE), 1))

    def get(self, order_id: int) -> Order | None:
        """Return one order with everything the detail page shows."""
        return self._orders.get_detail(order_id)

    def change_marker(self) -> str:
        """Return a text that changes when any order is placed or moves (for live refresh)."""
        return self._orders.change_marker()
