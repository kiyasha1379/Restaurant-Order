"""The admin "Customers" tab: who signed up, what they ordered, and blocking an account."""

from dataclasses import dataclass

from restaurant.models import Address, Order, Reservation, User
from restaurant.repositories import (
    AddressRepository,
    CustomerOrderStats,
    OrderRepository,
    ReservationRepository,
    UserRepository,
)

NO_ORDERS = CustomerOrderStats(order_count=0, total_spent=0, last_order_at=None)
DETAIL_ORDER_LIMIT = 20


@dataclass(frozen=True)
class CustomerRow:
    """One line of the customer list."""

    user: User
    stats: CustomerOrderStats
    reservation_count: int


@dataclass(frozen=True)
class CustomerDetail:
    """Everything the detail page shows about one customer."""

    user: User
    stats: CustomerOrderStats
    orders: list[Order]
    reservations: list[Reservation]
    addresses: list[Address]


class CustomerAdminService:
    """Reads customers for the panel and blocks or unblocks them."""

    def __init__(
        self,
        user_repository: UserRepository,
        order_repository: OrderRepository,
        reservation_repository: ReservationRepository,
        address_repository: AddressRepository,
    ) -> None:
        """Receive the repositories instead of importing them, so tests can swap them."""
        self._users = user_repository
        self._orders = order_repository
        self._reservations = reservation_repository
        self._addresses = address_repository

    def list_customers(self, text: str, offset: int, limit: int) -> tuple[list[CustomerRow], int]:
        """Return one page of customers with their order and reservation counts."""
        users, total = self._users.list_customers(text, offset, limit)
        ids = [user.id for user in users]
        stats = self._orders.stats_for_users(ids)
        reservation_counts = self._reservations.count_by_users(ids)
        rows = [
            CustomerRow(user, stats.get(user.id, NO_ORDERS), reservation_counts.get(user.id, 0))
            for user in users
        ]
        return rows, total

    def get_detail(self, user_id: int) -> CustomerDetail | None:
        """Return one customer with recent orders, reservations and addresses, or None."""
        user = self._users.get(user_id)
        if user is None or user.roles or user.registration_pending:
            return None
        orders, _ = self._orders.list_for_user(user.id, 0, DETAIL_ORDER_LIMIT)
        return CustomerDetail(
            user=user,
            stats=self._orders.stats_for_users([user.id]).get(user.id, NO_ORDERS),
            orders=orders,
            reservations=self._reservations.list_for_user(user.id),
            addresses=self._addresses.list_for_user(user.id),
        )

    def set_active(self, user_id: int, is_active: bool) -> bool:
        """Block (False) or unblock (True) a customer. Returns False for an unknown customer."""
        detail = self.get_detail(user_id)
        if detail is None:
            return False
        detail.user.is_active = is_active
        return True
