"""The numbers on the admin dashboard: today's orders and sales, busy hours and alerts."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from restaurant.constants import LANGUAGE_CODE_ENGLISH, OrderStatus
from restaurant.repositories import DishRepository, OrderRepository
from restaurant.services.translation_service import TranslationService
from restaurant.timeutils import now_tehran

ACTIVE_STATUSES = (
    OrderStatus.PLACED,
    OrderStatus.PREPARING,
    OrderStatus.READY,
    OrderStatus.OUT_FOR_DELIVERY,
)
HOURS_IN_DAY = 24
DEFAULT_FIRST_HOUR = 10
DEFAULT_LAST_HOUR = 22


@dataclass(frozen=True)
class DashboardData:
    """Everything the dashboard shows. Amounts are in whole tomans."""

    orders_today: int
    sales_today: int
    average_order: int
    orders_by_status: dict[OrderStatus, int]
    busy_hours: list[int] = field(default_factory=list)
    waiting_orders: int = 0
    out_of_stock_dishes: int = 0
    dishes_missing_english: int = 0
    texts_missing_english: int = 0

    @property
    def busiest_hour_count(self) -> int:
        """The height of the tallest bar in the busy-hours chart."""
        return max(self.busy_hours, default=0)

    @property
    def in_progress(self) -> int:
        """How many orders are not finished yet."""
        return sum(self.orders_by_status.get(status, 0) for status in ACTIVE_STATUSES)

    @property
    def visible_hours(self) -> range:
        """The hours the busy-hours chart shows: opening time as a default, wider if needed."""
        busy = [hour for hour, count in enumerate(self.busy_hours) if count]
        return range(min([DEFAULT_FIRST_HOUR, *busy]), max([DEFAULT_LAST_HOUR, *busy]) + 1)

    @property
    def alert_count(self) -> int:
        """How many things need attention."""
        return sum(
            1
            for amount in (
                self.waiting_orders,
                self.out_of_stock_dishes,
                self.dishes_missing_english,
                self.texts_missing_english,
            )
            if amount
        )


class DashboardService:
    """Collects the dashboard numbers for the current day (Tehran time)."""

    def __init__(
        self,
        order_repository: OrderRepository,
        dish_repository: DishRepository,
        translation_service: TranslationService,
        clock: Callable[[], datetime] = now_tehran,
    ) -> None:
        """Receive the collaborators and the clock, so tests can fix the time."""
        self._orders = order_repository
        self._dishes = dish_repository
        self._translations = translation_service
        self._clock = clock

    def today(self) -> DashboardData:
        """Return the dashboard numbers. Cancelled orders do not count as sales."""
        start = self._clock().replace(hour=0, minute=0, second=0, microsecond=0)
        orders = self._orders.list_between(start, start + timedelta(days=1))
        sold = [order for order in orders if order.status is not OrderStatus.CANCELLED]
        sales = sum(order.total for order in sold)
        hours = [0] * HOURS_IN_DAY
        for order in sold:
            hours[order.created_at.hour] += 1
        by_status = self._orders.count_by_status()
        return DashboardData(
            orders_today=len(sold),
            sales_today=sales,
            average_order=sales // len(sold) if sold else 0,
            orders_by_status=by_status,
            busy_hours=hours,
            waiting_orders=by_status.get(OrderStatus.PLACED, 0),
            out_of_stock_dishes=self._dishes.count_out_of_stock(),
            dishes_missing_english=self._dishes.count_without_translation(LANGUAGE_CODE_ENGLISH),
            texts_missing_english=len(self._translations.find_missing_keys(LANGUAGE_CODE_ENGLISH)),
        )

    def count_waiting_orders(self) -> int:
        """Return how many orders wait for the kitchen to accept them (the sidebar badge)."""
        return self._orders.count_by_status().get(OrderStatus.PLACED, 0)
