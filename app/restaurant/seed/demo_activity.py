"""A few sample orders and reservations so the demo dashboard and boards are not empty.

They are added only while the database holds no orders and no reservations, so running the
seed again (or after real use) never adds more. `reset-demo` brings them back.
"""

from datetime import timedelta

from restaurant.constants import FulfillmentType, PaymentMethod, ReservationStatus
from restaurant.repositories import (
    DishRepository,
    OrderRepository,
    ReservationRepository,
    TableRepository,
    UserRepository,
)
from restaurant.seed.demo_customers import DEMO_CUSTOMER_EMAIL
from restaurant.services import (
    BookingService,
    CartLine,
    OrderService,
    PlaceOrderRequest,
    ReservationRequest,
)
from restaurant.timeutils import now_tehran

# (customer, phone, fulfillment, payment, how many forward steps, dish positions with quantity)
DEMO_ORDERS = (
    (
        "سارا احمدی",
        "09121111111",
        FulfillmentType.TAKEAWAY,
        PaymentMethod.CASH_ON_SITE,
        0,
        ((0, 2), (4, 1)),
    ),
    (
        "John Miller",
        "09122222222",
        FulfillmentType.DELIVERY,
        PaymentMethod.CASH_ON_SITE,
        1,
        ((1, 1), (6, 2)),
    ),
    (
        "رضا کریمی",
        "09123333333",
        FulfillmentType.TAKEAWAY,
        PaymentMethod.CASH_ON_SITE,
        2,
        ((2, 1),),
    ),
    (
        "مریم حسینی",
        "09124444444",
        FulfillmentType.DELIVERY,
        PaymentMethod.CASH_ON_SITE,
        4,
        ((3, 2), (8, 2)),
    ),
    (
        "Demo Customer",
        "09120000000",
        FulfillmentType.TAKEAWAY,
        PaymentMethod.CASH_ON_SITE,
        3,
        ((5, 1), (7, 1)),
    ),
)
DEMO_DELIVERY_ADDRESS = "تهران، خیابان ولیعصر، پلاک ۱۲۰، واحد ۴"
# (customer, phone, guests, days from today, hour, confirmed)
DEMO_RESERVATIONS = (
    ("خانواده‌ی موسوی", "09125555555", 4, 0, 20, True),
    ("Emma Clarke", "09126666666", 2, 0, 21, False),
    ("علی نادری", "09127777777", 6, 1, 19, True),
)


class DemoActivitySeeder:
    """Adds sample orders in several states and a few bookings for today and tomorrow."""

    def __init__(
        self,
        order_service: OrderService,
        booking_service: BookingService,
        order_repository: OrderRepository,
        reservation_repository: ReservationRepository,
        dish_repository: DishRepository,
        table_repository: TableRepository,
        user_repository: UserRepository,
    ) -> None:
        """Receive the collaborators instead of importing them, so tests can swap them."""
        self._orders = order_service
        self._booking = booking_service
        self._order_repository = order_repository
        self._reservation_repository = reservation_repository
        self._dishes = dish_repository
        self._tables = table_repository
        self._users = user_repository

    def seed(self) -> int:
        """Add the sample rows when there are none; return how many orders and bookings."""
        if self._order_repository.count() or self._reservation_repository.count():
            return 0
        dishes = [dish for dish in self._dishes.list_all() if dish.is_visible and dish.is_in_stock]
        if not dishes:
            return 0
        return self._seed_orders(dishes) + self._seed_reservations()

    def _seed_orders(self, dishes: list) -> int:
        """Place the sample orders and move each some steps forward."""
        customer = self._users.get_by_email(DEMO_CUSTOMER_EMAIL)
        added = 0
        for name, phone, fulfillment, payment, steps, picks in DEMO_ORDERS:
            lines = [
                CartLine(
                    f"dish-{dishes[position % len(dishes)].id}",
                    dishes[position % len(dishes)].id,
                    quantity,
                )
                for position, quantity in picks
            ]
            request = PlaceOrderRequest(
                customer_name=name,
                customer_phone=phone,
                fulfillment=fulfillment,
                delivery_address=(
                    DEMO_DELIVERY_ADDRESS if fulfillment is FulfillmentType.DELIVERY else ""
                ),
                note="",
                payment_method=payment,
                language_code="en" if name.isascii() else "fa",
                user_id=customer.id if customer and phone == customer.phone else None,
            )
            order = self._orders.place_order(request, lines)
            for _ in range(steps):
                self._orders.advance(order)
            added += 1
        return added

    def _seed_reservations(self) -> int:
        """Book the sample tables with staff rights, so the notice time does not matter."""
        now = now_tehran()
        tables = self._tables.list_ordered(only_active=True)
        added = 0
        for name, phone, guests, day_offset, hour, confirmed in DEMO_RESERVATIONS:
            table = next((table for table in tables if table.capacity >= guests), None)
            if table is None:
                continue
            day = (now + timedelta(days=day_offset)).date()
            status = ReservationStatus.CONFIRMED if confirmed else ReservationStatus.PENDING
            self._booking.reserve(
                ReservationRequest(
                    day=day,
                    start=now.replace(hour=hour, minute=0, second=0, microsecond=0).time(),
                    guests=guests,
                    table_id=table.id,
                    customer_name=name,
                    customer_phone=phone,
                    language_code="en" if name.isascii() else "fa",
                ),
                now,
                by_staff=True,
                status=status,
            )
            tables.remove(table)  # one table each, so the three bookings never clash
            added += 1
        return added
