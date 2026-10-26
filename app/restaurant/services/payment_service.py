"""Paying orders: starting an online payment, finishing it, and recording cash.

Money rules in one place (technical plan, section 8):

- An online order is `awaiting_payment` until `PaymentGateway.verify()` says the payment
  succeeded. Nothing else, not even the page the customer returns to, can mark it paid.
- A failed or cancelled attempt leaves the order waiting; the customer may try again or
  pay on arrival instead.
- A finished attempt never changes again, so a repeated callback is harmless.
- No card data is ever collected or stored.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy.orm import Session

from restaurant.constants import OrderStatus, PaymentMethod, PaymentStatus
from restaurant.models import Order, Payment
from restaurant.repositories import PaymentRepository
from restaurant.services.order_service import OrderService
from restaurant.services.payment_gateway import (
    GatewayError,
    GatewayOutcome,
    PaymentGateway,
    StartRequest,
)
from restaurant.timeutils import now_tehran
from restaurant.transactions import begin_immediate


class PaymentProblem(StrEnum):
    """Why a payment action was refused; the page turns it into a message."""

    NOT_PAYABLE = "not_payable"
    UNKNOWN_PAYMENT = "unknown_payment"
    WRONG_GATEWAY = "wrong_gateway"
    GATEWAY_UNAVAILABLE = "gateway_unavailable"
    NOT_CASH = "not_cash"


class PaymentError(ValueError):
    """A payment action was refused. `problem` says why."""

    def __init__(self, problem: PaymentProblem) -> None:
        """Keep the reason so callers can pick the right message."""
        super().__init__(problem.value)
        self.problem = problem


@dataclass(frozen=True)
class StartedPayment:
    """A payment attempt that was registered, and where to send the customer."""

    payment: Payment
    redirect_url: str


@dataclass(frozen=True)
class PaymentResult:
    """What happened when the customer came back. `repeated` is True for a second callback."""

    payment: Payment
    order: Order
    repeated: bool = False


class PaymentService:
    """Runs payments through the gateway and keeps orders and payments consistent."""

    def __init__(
        self,
        session: Session,
        payment_repository: PaymentRepository,
        order_service: OrderService,
        gateway: PaymentGateway,
        clock: Callable[[], datetime] = now_tehran,
    ) -> None:
        """Receive the collaborators and the clock, so tests can swap them."""
        self._session = session
        self._payments = payment_repository
        self._orders = order_service
        self._gateway = gateway
        self._clock = clock

    @property
    def gateway_name(self) -> str:
        """The name of the configured gateway (it appears in the callback address)."""
        return self._gateway.name

    def start_online(self, order: Order, callback_url: str, language_code: str) -> StartedPayment:
        """Register a new online attempt for an order that waits for payment.

        An earlier open attempt is abandoned. The caller commits. Raises PaymentError.
        """
        if (
            order.payment_method is not PaymentMethod.ONLINE
            or order.status is not OrderStatus.AWAITING_PAYMENT
        ):
            raise PaymentError(PaymentProblem.NOT_PAYABLE)
        try:
            started = self._gateway.start(
                StartRequest(order.number, order.total, callback_url, language_code)
            )
        except GatewayError as error:
            raise PaymentError(PaymentProblem.GATEWAY_UNAVAILABLE) from error
        for earlier in order.payments:
            if earlier.status is PaymentStatus.PENDING:
                earlier.status = PaymentStatus.CANCELLED
        payment = Payment(
            order=order,
            method=PaymentMethod.ONLINE,
            gateway=self._gateway.name,
            status=PaymentStatus.PENDING,
            amount=order.total,
            authority=started.authority,
        )
        self._payments.add(payment)
        return StartedPayment(payment, started.redirect_url)

    def find_open_payment(self, authority: str) -> Payment | None:
        """Return the attempt with this reference while it is still waiting, else None."""
        payment = self._payments.get_by_authority(authority)
        if payment is None or payment.status is not PaymentStatus.PENDING:
            return None
        return payment

    def authority_from(self, params: Mapping[str, str]) -> str:
        """Read the payment reference out of what the gateway sent back."""
        return self._gateway.authority_from(params)

    def complete(self, params: Mapping[str, str]) -> PaymentResult:
        """Finish an attempt from the gateway's callback. The caller commits.

        The gateway is asked (`verify`) before anything is stored, and the answer is
        applied under the database write lock, so two callbacks cannot both win.
        Raises PaymentError for an unknown attempt or one made with another gateway.
        """
        payment = self._payments.get_by_authority(self._gateway.authority_from(params))
        if payment is None:
            raise PaymentError(PaymentProblem.UNKNOWN_PAYMENT)
        if payment.gateway != self._gateway.name:
            raise PaymentError(PaymentProblem.WRONG_GATEWAY)
        if payment.status is not PaymentStatus.PENDING:
            return PaymentResult(payment, payment.order, repeated=True)
        try:
            verdict = self._gateway.verify(payment.authority, payment.amount, params)
        except GatewayError as error:
            raise PaymentError(PaymentProblem.GATEWAY_UNAVAILABLE) from error

        begin_immediate(self._session)
        self._payments.refresh(payment)
        if payment.status is not PaymentStatus.PENDING:
            return PaymentResult(payment, payment.order, repeated=True)
        if verdict.outcome is GatewayOutcome.PAID and verdict.amount == payment.amount:
            payment.status = PaymentStatus.PAID
            payment.transaction_id = verdict.transaction_id
            payment.paid_at = self._clock()
            if payment.order.status is OrderStatus.AWAITING_PAYMENT:
                self._orders.confirm_payment(payment.order)
        elif verdict.outcome is GatewayOutcome.CANCELLED:
            payment.status = PaymentStatus.CANCELLED
        else:
            # A failure, or a "paid" answer for the wrong amount: never trust it.
            payment.status = PaymentStatus.FAILED
        return PaymentResult(payment, payment.order)

    def switch_to_cash(self, order: Order) -> Order:
        """Let a customer whose online payment did not work pay on arrival instead.

        The order enters the kitchen's queue with an open pay-on-site payment.
        The caller commits. Raises PaymentError.
        """
        if (
            order.payment_method is not PaymentMethod.ONLINE
            or order.status is not OrderStatus.AWAITING_PAYMENT
            or order.is_paid
        ):
            raise PaymentError(PaymentProblem.NOT_PAYABLE)
        for earlier in order.payments:
            if earlier.status is PaymentStatus.PENDING:
                earlier.status = PaymentStatus.CANCELLED
        order.payment_method = PaymentMethod.CASH_ON_SITE
        self._payments.add(
            Payment(
                order=order,
                method=PaymentMethod.CASH_ON_SITE,
                status=PaymentStatus.PENDING,
                amount=order.total,
            )
        )
        return self._orders.confirm_payment(order)

    def mark_cash_received(self, order: Order) -> Payment:
        """Record that staff took the money of a pay-on-site order. The caller commits.

        Raises PaymentError when the order is not a pay-on-site order that can be paid now.
        """
        if order.payment_method is not PaymentMethod.CASH_ON_SITE or order.status in (
            OrderStatus.AWAITING_PAYMENT,
            OrderStatus.CANCELLED,
        ):
            raise PaymentError(PaymentProblem.NOT_CASH)
        for payment in order.payments:
            if payment.status is PaymentStatus.PENDING:
                payment.status = PaymentStatus.PAID
                payment.paid_at = self._clock()
                return payment
        raise PaymentError(PaymentProblem.NOT_CASH)
