"""Placing orders and moving them through their statuses."""

import secrets
from dataclasses import dataclass

from restaurant.constants import FulfillmentType, OrderStatus, PaymentMethod, PaymentStatus
from restaurant.models import Order, OrderItem, OrderItemOption, OrderStatusLog, Payment
from restaurant.repositories import OrderRepository
from restaurant.services.cart_service import CartLine
from restaurant.services.order_status import OrderStatusMachine
from restaurant.services.pricing_service import PricedCart, PricingService

TOKEN_BYTES = 9


class OrderError(ValueError):
    """The order cannot be placed or changed."""


class EmptyCartError(OrderError):
    """There is nothing to order."""


class UnavailableDishError(OrderError):
    """A dish in the cart can no longer be ordered."""

    def __init__(self, line_ids: set[str]) -> None:
        """Keep the lines so the page can remove them from the cart."""
        super().__init__("Some dishes are no longer available")
        self.line_ids = line_ids


class InvalidTransitionError(OrderError):
    """The order may not move to that status from where it is."""


@dataclass(frozen=True)
class PlaceOrderRequest:
    """Everything the customer typed at checkout, already validated."""

    customer_name: str
    customer_phone: str
    fulfillment: FulfillmentType
    delivery_address: str
    note: str
    payment_method: PaymentMethod
    language_code: str
    user_id: int | None = None


class OrderService:
    """Creates orders from a cart and changes their status."""

    def __init__(self, order_repository: OrderRepository, pricing_service: PricingService) -> None:
        """Receive the repository and pricing instead of importing them, so tests can swap them."""
        self._order_repository = order_repository
        self._pricing_service = pricing_service

    def place_order(self, request: PlaceOrderRequest, cart_lines: list[CartLine]) -> Order:
        """Price the cart on the server and store the order with snapshot names and prices.

        The caller commits. Raises EmptyCartError or UnavailableDishError.
        """
        priced = self._pricing_service.price(cart_lines, request.fulfillment, request.language_code)
        if priced.unavailable_line_ids:
            raise UnavailableDishError(priced.unavailable_line_ids)
        if not priced.lines:
            raise EmptyCartError("The cart is empty")
        order = self._build_order(request, priced)
        order.status_log.append(OrderStatusLog(from_status=None, to_status=order.status))
        self._order_repository.add(order)
        return order

    def change_status(
        self, order: Order, target: OrderStatus, changed_by_user_id: int | None = None
    ) -> Order:
        """Move the order to `target` if the state rules allow it. The caller commits."""
        if not OrderStatusMachine.can_move(order.status, target, order.fulfillment):
            raise InvalidTransitionError(f"Cannot move from {order.status} to {target}")
        order.status_log.append(
            OrderStatusLog(
                from_status=order.status, to_status=target, changed_by_user_id=changed_by_user_id
            )
        )
        order.status = target
        if target is OrderStatus.CANCELLED:
            self._close_open_payments(order)
        return order

    def confirm_payment(self, order: Order) -> Order:
        """Let an order that waited for its payment into the kitchen's queue.

        Called only after a payment was verified, or when the customer chose to pay on
        arrival instead. The caller commits.
        """
        if order.status is not OrderStatus.AWAITING_PAYMENT:
            raise InvalidTransitionError(f"Order is not waiting for payment: {order.status}")
        order.status_log.append(
            OrderStatusLog(from_status=order.status, to_status=OrderStatus.PLACED)
        )
        order.status = OrderStatus.PLACED
        return order

    @staticmethod
    def _close_open_payments(order: Order) -> None:
        """Cancel the payments of a cancelled order that nobody has paid yet."""
        for payment in order.payments:
            if payment.status is PaymentStatus.PENDING:
                payment.status = PaymentStatus.CANCELLED

    def advance(self, order: Order, changed_by_user_id: int | None = None) -> Order:
        """Move the order one normal step forward (used by the demo and the kitchen board)."""
        target = OrderStatusMachine.forward_step(order.status, order.fulfillment)
        if target is None:
            raise InvalidTransitionError("The order is already finished")
        return self.change_status(order, target, changed_by_user_id)

    def read_status(self, order_id: int) -> OrderStatus:
        """Return the stored status of an order (fresh from the database)."""
        order = self._order_repository.get(order_id)
        if order is None:
            raise OrderError("Unknown order")
        self._order_repository.refresh(order)
        return order.status

    def get(self, order_id: int) -> Order | None:
        """Return the order with this id, or None."""
        return self._order_repository.get(order_id)

    def list_for_user(self, user_id: int, offset: int, limit: int) -> tuple[list[Order], int]:
        """Return one page of a customer's orders (newest first) and how many they have."""
        return self._order_repository.list_for_user(user_id, offset, limit)

    def find_for_user(self, user_id: int, public_token: str) -> Order | None:
        """Return the order behind this token only when it belongs to the customer."""
        return self._order_repository.get_for_user(user_id, public_token)

    def find_by_token(self, public_token: str) -> Order | None:
        """Return the order behind a tracking address, or None."""
        return self._order_repository.get_by_token(public_token)

    @staticmethod
    def _build_order(request: PlaceOrderRequest, priced: PricedCart) -> Order:
        """Create the order row and its lines from the priced cart."""
        is_delivery = request.fulfillment is FulfillmentType.DELIVERY
        pays_online = request.payment_method is PaymentMethod.ONLINE
        # An online order waits for its payment; the payment attempt is created when it starts.
        # Pay on site starts with one open payment that staff mark as received.
        payments = (
            []
            if pays_online
            else [
                Payment(
                    method=PaymentMethod.CASH_ON_SITE,
                    status=PaymentStatus.PENDING,
                    amount=priced.total,
                )
            ]
        )
        return Order(
            public_token=secrets.token_urlsafe(TOKEN_BYTES),
            user_id=request.user_id,
            language_code=request.language_code,
            customer_name=request.customer_name,
            customer_phone=request.customer_phone,
            fulfillment=request.fulfillment,
            delivery_address=request.delivery_address if is_delivery else "",
            note=request.note,
            payment_method=request.payment_method,
            status=OrderStatus.AWAITING_PAYMENT if pays_online else OrderStatus.PLACED,
            payments=payments,
            subtotal=priced.subtotal,
            delivery_fee=priced.delivery_fee,
            total=priced.total,
            items=[
                OrderItem(
                    dish_id=line.dish_id,
                    builder_id=line.builder_id,
                    name_fa=line.name_fa,
                    name_en=line.name_en,
                    unit_price=line.unit_price,
                    quantity=line.quantity,
                    line_total=line.line_total,
                    options=[
                        OrderItemOption(
                            order_index=option.order_index,
                            option_id=option.option_id,
                            name_fa=option.name_fa,
                            name_en=option.name_en,
                            group_fa=option.group_fa,
                            group_en=option.group_en,
                            price=option.price,
                        )
                        for option in line.options
                    ],
                )
                for line in priced.lines
            ],
        )
