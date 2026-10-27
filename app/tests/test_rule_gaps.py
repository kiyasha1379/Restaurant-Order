"""Small rule checks that the phase-11 coverage report showed as untested."""

import pytest

from restaurant.constants import OrderStatus, PaymentMethod
from restaurant.extensions import db
from restaurant.models import Payment
from restaurant.service_factory import make_booking_service, make_order_service
from restaurant.services import (
    BookingError,
    BookingProblem,
    CartService,
    GatewayError,
    InvalidTransitionError,
    MockGateway,
    OrderError,
    PaymentError,
    PaymentProblem,
)
from tests.test_booking_service import NOW, reserve, tables  # noqa: F401
from tests.test_cart_service import FakeStorage
from tests.test_payments import answer, dish, make_service, place, started  # noqa: F401


def test_changing_the_table_of_a_cancelled_booking_is_refused(tables) -> None:  # noqa: F811
    booking = reserve(tables[1])
    service = make_booking_service()
    service.cancel(booking)
    db.session.commit()
    with pytest.raises(BookingError) as error:
        service.change_table(booking, tables[2].id)
    assert error.value.problem is BookingProblem.ALREADY_CANCELLED


def test_only_an_order_waiting_for_payment_can_be_released(dish) -> None:  # noqa: F811
    order = place(dish, PaymentMethod.CASH_ON_SITE)
    with pytest.raises(InvalidTransitionError):
        make_order_service().confirm_payment(order)
    assert order.status is OrderStatus.PLACED


def test_reading_the_status_of_a_missing_order_says_so(app) -> None:
    with pytest.raises(OrderError):
        make_order_service().read_status(999)


def test_a_gateway_that_is_down_keeps_the_attempt_open(dish) -> None:  # noqa: F811
    class Down(MockGateway):
        def verify(self, authority, amount, params):
            raise GatewayError("bank offline")

    order = place(dish)
    service = make_service(Down(lambda authority, language: "/x"))
    payment = started(service, order).payment
    with pytest.raises(PaymentError) as error:
        service.complete(answer(payment.authority, {"status": "ok"}))
    assert error.value.problem is PaymentProblem.GATEWAY_UNAVAILABLE
    assert payment.status.value == "pending" and not order.is_paid


def test_an_attempt_made_with_another_gateway_is_not_completed_here(dish) -> None:  # noqa: F811
    order = place(dish)
    service = make_service()
    payment = started(service, order).payment
    payment.gateway = "other-bank"
    db.session.commit()
    with pytest.raises(PaymentError) as error:
        service.complete(answer(payment.authority, {"status": "ok"}))
    assert error.value.problem is PaymentProblem.WRONG_GATEWAY
    assert db.session.query(Payment).count() == 1


def test_starting_a_payment_with_online_payment_off_explains_instead_of_crashing(
    app, dish  # noqa: F811
) -> None:
    order = place(dish)
    app.config["PAYMENT_GATEWAY"] = ""
    client = app.test_client()
    response = client.post(f"/fa/pay/{order.public_token}/start")
    assert response.status_code == 302 and f"/order/{order.public_token}" in response.location


def test_saved_cart_lines_beyond_the_limit_and_broken_lines_are_dropped() -> None:
    cart = CartService(FakeStorage())
    saved = [{"line_id": f"dish-{n}", "dish_id": n, "quantity": 1} for n in range(1, 31)]
    cart.merge_saved([*saved, {"nonsense": True}, "text", None])
    assert len(cart.lines()) == 25
    cart.merge_saved([{"line_id": "dish-1", "dish_id": 1, "quantity": 2}])
    assert next(line for line in cart.lines() if line.line_id == "dish-1").quantity == 3
