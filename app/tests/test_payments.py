"""Online payment: the gateway interface, the payment service, the pages and the admin view."""

import pytest

from restaurant.constants import FulfillmentType, OrderStatus, PaymentMethod, PaymentStatus
from restaurant.extensions import db
from restaurant.models import Order, Payment
from restaurant.repositories import PaymentRepository
from restaurant.service_factory import make_order_service
from restaurant.services import (
    CartLine,
    GatewayError,
    GatewayOutcome,
    MockGateway,
    OrderService,
    PaymentError,
    PaymentGateway,
    PaymentProblem,
    PaymentService,
    PlaceOrderRequest,
    StartRequest,
    StartResult,
    UnknownGatewayError,
    VerifyResult,
    create_gateway,
)
from tests.helpers import add_category, add_dish, staff_client

OK = {"status": "ok"}
FAILED = {"status": "failed"}
CANCEL = {"status": "cancel"}


@pytest.fixture
def dish(app):
    category = add_category("a", {"fa": "الف", "en": "A"})
    kebab = add_dish(category, {"fa": "کباب", "en": "Kebab"}, base_price=280_000)
    db.session.commit()
    return kebab


def place(dish, method=PaymentMethod.ONLINE) -> Order:
    """Place an order the way checkout does and return it."""
    order = make_order_service().place_order(
        PlaceOrderRequest(
            customer_name="Ali",
            customer_phone="09123456789",
            fulfillment=FulfillmentType.TAKEAWAY,
            delivery_address="",
            note="",
            payment_method=method,
            language_code="fa",
        ),
        [CartLine(f"dish-{dish.id}", dish.id, 1)],
    )
    db.session.commit()
    return order


def make_service(gateway: PaymentGateway | None = None) -> PaymentService:
    return PaymentService(
        db.session,
        PaymentRepository(db.session),
        OrderService(make_order_service()._order_repository, make_order_service()._pricing_service),
        gateway or MockGateway(lambda authority, language: f"/gateway/{language}/{authority}"),
    )


def started(service: PaymentService, order: Order):
    result = service.start_online(order, "https://shop.test/callback", "fa")
    db.session.commit()
    return result


def answer(authority: str, params: dict) -> dict:
    return {"authority": authority, **params}


# --- the test gateway ----------------------------------------------------------------------


def test_mock_gateway_start_gives_a_reference_and_its_page():
    gateway = MockGateway(lambda authority, language: f"/pay/{language}/{authority}")
    result = gateway.start(StartRequest(7, 100_000, "https://x/cb", "en"))
    assert result.authority.startswith("MOCKA-")
    assert result.redirect_url == f"/pay/en/{result.authority}"
    assert (
        gateway.start(StartRequest(7, 100_000, "https://x/cb", "en")).authority != result.authority
    )


def test_mock_gateway_verify_maps_the_answers():
    gateway = MockGateway(lambda authority, language: "")
    paid = gateway.verify("A", 5_000, OK)
    assert (paid.outcome, paid.amount) == (GatewayOutcome.PAID, 5_000)
    assert paid.transaction_id.startswith("MOCK-")
    assert gateway.verify("A", 5_000, CANCEL).outcome is GatewayOutcome.CANCELLED
    assert gateway.verify("A", 5_000, FAILED).outcome is GatewayOutcome.FAILED
    assert gateway.verify("A", 5_000, {}).outcome is GatewayOutcome.FAILED
    assert gateway.verify("A", 5_000, {"status": "OK"}).outcome is GatewayOutcome.FAILED
    assert gateway.authority_from({"authority": "X"}) == "X" and gateway.authority_from({}) == ""


def test_the_factory_builds_the_named_gateway_only():
    assert isinstance(create_gateway("mock", lambda a, b: ""), MockGateway)
    for name in ("", "unknown"):
        with pytest.raises(UnknownGatewayError):
            create_gateway(name, lambda a, b: "")


# --- placing orders ------------------------------------------------------------------------


def test_cash_order_starts_placed_with_one_open_cash_payment(dish):
    order = place(dish, PaymentMethod.CASH_ON_SITE)
    assert order.status is OrderStatus.PLACED
    (payment,) = order.payments
    assert (payment.method, payment.status, payment.amount) == (
        PaymentMethod.CASH_ON_SITE,
        PaymentStatus.PENDING,
        280_000,
    )
    assert payment.gateway == "" and not payment.is_test and not order.is_paid


def test_online_order_waits_for_payment_and_has_no_attempt_yet(dish):
    order = place(dish)
    assert order.status is OrderStatus.AWAITING_PAYMENT
    assert order.payments == [] and not order.is_paid
    assert [entry.to_status for entry in order.status_log] == [OrderStatus.AWAITING_PAYMENT]


# --- the payment service -------------------------------------------------------------------


def test_start_registers_a_pending_attempt_and_keeps_the_order_waiting(dish):
    order = place(dish)
    result = started(make_service(), order)
    payment = result.payment
    assert (payment.method, payment.status, payment.gateway) == (
        PaymentMethod.ONLINE,
        PaymentStatus.PENDING,
        "mock",
    )
    assert payment.amount == order.total and payment.is_test
    assert result.redirect_url == f"/gateway/fa/{payment.authority}"
    assert order.status is OrderStatus.AWAITING_PAYMENT


def test_a_verified_payment_marks_it_paid_and_sends_the_order_to_the_kitchen(dish):
    order = place(dish)
    service = make_service()
    payment = started(service, order).payment
    result = service.complete(answer(payment.authority, OK))
    db.session.commit()
    assert not result.repeated
    assert payment.status is PaymentStatus.PAID and payment.transaction_id.startswith("MOCK-")
    assert payment.paid_at is not None and order.is_paid
    assert order.status is OrderStatus.PLACED
    assert [entry.to_status for entry in order.status_log] == [
        OrderStatus.AWAITING_PAYMENT,
        OrderStatus.PLACED,
    ]


@pytest.mark.parametrize(
    ("params", "expected"),
    [(FAILED, PaymentStatus.FAILED), (CANCEL, PaymentStatus.CANCELLED), ({}, PaymentStatus.FAILED)],
)
def test_a_failed_or_cancelled_payment_leaves_the_order_waiting(dish, params, expected):
    order = place(dish)
    service = make_service()
    payment = started(service, order).payment
    service.complete(answer(payment.authority, params))
    db.session.commit()
    assert payment.status is expected and payment.paid_at is None
    assert order.status is OrderStatus.AWAITING_PAYMENT and not order.is_paid


def test_a_retry_abandons_the_open_attempt_and_can_still_succeed(dish):
    order = place(dish)
    service = make_service()
    first = started(service, order).payment
    service.complete(answer(first.authority, FAILED))
    db.session.commit()
    second = started(service, order).payment
    third = started(service, order).payment
    db.session.refresh(second)
    assert second.status is PaymentStatus.CANCELLED and third.status is PaymentStatus.PENDING
    service.complete(answer(third.authority, OK))
    db.session.commit()
    assert order.is_paid and order.status is OrderStatus.PLACED
    assert [p.status for p in order.payments] == [
        PaymentStatus.FAILED,
        PaymentStatus.CANCELLED,
        PaymentStatus.PAID,
    ]


def test_a_finished_payment_never_changes_again(dish):
    order = place(dish)
    service = make_service()
    payment = started(service, order).payment
    service.complete(answer(payment.authority, OK))
    db.session.commit()
    transaction = payment.transaction_id
    for params in (OK, FAILED, CANCEL):
        again = service.complete(answer(payment.authority, params))
        assert again.repeated and again.payment.status is PaymentStatus.PAID
    assert payment.transaction_id == transaction and len(order.payments) == 1


def test_an_unknown_reference_is_refused(dish):
    place(dish)
    for params in ({}, {"authority": "MOCKA-nothing"}):
        with pytest.raises(PaymentError) as error:
            make_service().complete(params)
        assert error.value.problem is PaymentProblem.UNKNOWN_PAYMENT


def test_a_paid_answer_for_the_wrong_amount_is_not_trusted(dish):
    class Underpaying(MockGateway):
        def verify(self, authority, amount, params):
            return VerifyResult(GatewayOutcome.PAID, "MOCK-SHORT", amount - 1)

    order = place(dish)
    service = make_service(Underpaying(lambda authority, language: "/x"))
    payment = started(service, order).payment
    service.complete(answer(payment.authority, OK))
    db.session.commit()
    assert payment.status is PaymentStatus.FAILED and not order.is_paid
    assert order.status is OrderStatus.AWAITING_PAYMENT


def test_a_gateway_that_is_down_stores_nothing(dish):
    class Down(PaymentGateway):
        name = "mock"

        def start(self, request: StartRequest) -> StartResult:
            raise GatewayError("down")

        def authority_from(self, params):
            return params.get("authority", "")

        def verify(self, authority, amount, params):
            raise GatewayError("down")

    order = place(dish)
    with pytest.raises(PaymentError) as error:
        make_service(Down()).start_online(order, "https://x/cb", "fa")
    assert error.value.problem is PaymentProblem.GATEWAY_UNAVAILABLE
    db.session.rollback()
    assert db.session.query(Payment).count() == 0


def test_only_an_online_order_that_waits_can_start_a_payment(dish):
    service = make_service()
    cash = place(dish, PaymentMethod.CASH_ON_SITE)
    with pytest.raises(PaymentError):
        service.start_online(cash, "https://x/cb", "fa")
    paid = place(dish)
    payment = started(service, paid).payment
    service.complete(answer(payment.authority, OK))
    db.session.commit()
    with pytest.raises(PaymentError):
        service.start_online(paid, "https://x/cb", "fa")


def test_switching_to_cash_cancels_the_attempt_and_releases_the_order(dish):
    order = place(dish)
    service = make_service()
    attempt = started(service, order).payment
    service.switch_to_cash(order)
    db.session.commit()
    assert attempt.status is PaymentStatus.CANCELLED
    assert order.payment_method is PaymentMethod.CASH_ON_SITE
    assert order.status is OrderStatus.PLACED
    assert order.latest_payment.method is PaymentMethod.CASH_ON_SITE
    assert order.latest_payment.status is PaymentStatus.PENDING
    # The abandoned gateway reference can no longer pay the order.
    late = service.complete(answer(attempt.authority, OK))
    assert late.repeated and not order.is_paid


def test_switching_to_cash_is_refused_for_paid_or_cash_orders(dish):
    service = make_service()
    with pytest.raises(PaymentError):
        service.switch_to_cash(place(dish, PaymentMethod.CASH_ON_SITE))
    paid = place(dish)
    payment = started(service, paid).payment
    service.complete(answer(payment.authority, OK))
    db.session.commit()
    with pytest.raises(PaymentError):
        service.switch_to_cash(paid)


def test_staff_can_record_the_cash_once(dish):
    order = place(dish, PaymentMethod.CASH_ON_SITE)
    service = make_service()
    service.mark_cash_received(order)
    db.session.commit()
    assert order.is_paid and order.latest_payment.paid_at is not None
    with pytest.raises(PaymentError):
        service.mark_cash_received(order)


def test_cash_cannot_be_recorded_for_online_or_cancelled_orders(dish):
    service = make_service()
    with pytest.raises(PaymentError):
        service.mark_cash_received(place(dish))
    cancelled = place(dish, PaymentMethod.CASH_ON_SITE)
    make_order_service().change_status(cancelled, OrderStatus.CANCELLED)
    with pytest.raises(PaymentError):
        service.mark_cash_received(cancelled)


def test_cancelling_an_order_cancels_its_open_payments(dish):
    order = place(dish)
    attempt = started(make_service(), order).payment
    make_order_service().change_status(order, OrderStatus.CANCELLED)
    db.session.commit()
    assert order.status is OrderStatus.CANCELLED and attempt.status is PaymentStatus.CANCELLED
    late = make_service().complete(answer(attempt.authority, OK))
    assert late.repeated and not order.is_paid and order.status is OrderStatus.CANCELLED


def test_an_order_waiting_for_payment_can_only_be_cancelled(dish):
    order = place(dish)
    service = make_order_service()
    from restaurant.services import InvalidTransitionError

    for target in (OrderStatus.PLACED, OrderStatus.PREPARING, OrderStatus.COMPLETED):
        with pytest.raises(InvalidTransitionError):
            service.change_status(order, target)
    with pytest.raises(InvalidTransitionError):
        service.advance(order)


# --- pages ---------------------------------------------------------------------------------

CHECKOUT = {
    "customer_name": "علی رضایی",
    "customer_phone": "09123456789",
    "fulfillment": "takeaway",
    "delivery_address": "",
    "note": "",
    "payment_method": "online",
}


def checkout_online(client, dish, lang="fa", **overrides):
    client.post("/api/cart/add", json={"dish_id": dish.id, "quantity": 1})
    return client.post(f"/{lang}/checkout", data={**CHECKOUT, **overrides})


def authority_of(response) -> str:
    return response.headers["Location"].rsplit("/", 1)[-1]


def test_checkout_offers_online_payment_and_sends_the_customer_to_the_gateway(client, dish):
    client.post("/api/cart/add", json={"dish_id": dish.id, "quantity": 1})
    assert 'value="online"' in client.get("/fa/checkout").get_data(as_text=True)
    response = client.post("/fa/checkout", data=CHECKOUT)
    assert response.status_code == 302 and "/fa/pay/mock/MOCKA-" in response.headers["Location"]
    order = db.session.query(Order).one()
    assert order.status is OrderStatus.AWAITING_PAYMENT and order.payment_method.value == "online"
    assert order.latest_payment.authority == authority_of(response)
    assert client.get("/api/cart").get_json()["count"] == 0


def test_online_payment_is_not_offered_when_no_gateway_is_configured(app, client, dish):
    app.config["PAYMENT_GATEWAY"] = ""
    client.post("/api/cart/add", json={"dish_id": dish.id, "quantity": 1})
    assert 'value="online"' not in client.get("/fa/checkout").get_data(as_text=True)
    response = client.post("/fa/checkout", data=CHECKOUT)
    assert response.status_code == 200 and db.session.query(Order).count() == 0
    assert "پرداخت آنلاین در حال حاضر در دسترس نیست" in response.get_data(as_text=True)


@pytest.mark.parametrize("lang", ["fa", "en"])
def test_the_gateway_page_is_marked_as_a_test_and_has_no_card_form(client, dish, lang):
    response = checkout_online(client, dish, lang)
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "pay-gateway.css" in page and 'data-outcome="success"' in page
    assert 'data-outcome="failure"' in page and 'data-outcome="cancel"' in page
    assert "<input" not in page and "<form" not in page
    assert ("درگاه پرداخت آزمایشی" if lang == "fa" else "Test payment gateway") in page
    assert ("هیچ مبلغی کسر نمی‌شود" if lang == "fa" else "No money is charged") in page


def test_the_gateway_page_is_gone_for_unknown_or_finished_attempts(client, dish):
    response = checkout_online(client, dish)
    authority = authority_of(response)
    assert client.get("/fa/pay/mock/MOCKA-nothing").status_code == 404
    client.get(f"/fa/pay/callback/mock?authority={authority}&status=ok")
    assert client.get(f"/fa/pay/mock/{authority}").status_code == 404


def test_a_successful_payment_returns_to_a_paid_tracking_page(client, dish):
    authority = authority_of(checkout_online(client, dish))
    back = client.get(f"/fa/pay/callback/mock?authority={authority}&status=ok")
    order = db.session.query(Order).one()
    assert back.status_code == 302 and back.headers["Location"].endswith(
        f"/fa/order/{order.public_token}"
    )
    assert order.status is OrderStatus.PLACED and order.is_paid
    page = client.get(back.headers["Location"]).get_data(as_text=True)
    assert "پرداخت با موفقیت انجام شد" in page and "پرداخت آنلاین انجام شد" in page
    assert "data-pay-panel" not in page


def test_a_failed_payment_leaves_the_retry_panel(client, dish):
    authority = authority_of(checkout_online(client, dish, "en"))
    back = client.get(f"/en/pay/callback/mock?authority={authority}&status=failed")
    order = db.session.query(Order).one()
    assert order.status is OrderStatus.AWAITING_PAYMENT and not order.is_paid
    page = client.get(back.headers["Location"]).get_data(as_text=True)
    assert "The payment failed" in page and "data-pay-panel" in page
    assert "Pay online again" in page and "Pay on arrival instead" in page
    assert "Waiting for payment" in page
    assert "order/" in back.headers["Location"] and "demo_advance" not in page


def test_a_cancelled_payment_says_so(client, dish):
    authority = authority_of(checkout_online(client, dish))
    back = client.get(f"/fa/pay/callback/mock?authority={authority}&status=cancel")
    assert "پرداخت لغو شد" in client.get(back.headers["Location"]).get_data(as_text=True)
    assert db.session.query(Order).one().latest_payment.status is PaymentStatus.CANCELLED


def test_retrying_goes_to_a_fresh_gateway_page_and_can_then_succeed(client, dish):
    first = authority_of(checkout_online(client, dish))
    client.get(f"/fa/pay/callback/mock?authority={first}&status=failed")
    order = db.session.query(Order).one()
    retry = client.post(f"/fa/pay/{order.public_token}/start")
    second = authority_of(retry)
    assert second != first and "/fa/pay/mock/" in retry.headers["Location"]
    client.get(f"/fa/pay/callback/mock?authority={second}&status=ok")
    db.session.refresh(order)
    assert order.is_paid and order.status is OrderStatus.PLACED
    assert [p.status for p in order.payments] == [PaymentStatus.FAILED, PaymentStatus.PAID]


def test_choosing_to_pay_on_arrival_after_a_failure(client, dish):
    authority = authority_of(checkout_online(client, dish))
    client.get(f"/fa/pay/callback/mock?authority={authority}&status=cancel")
    order = db.session.query(Order).one()
    response = client.post(f"/fa/pay/{order.public_token}/cash")
    assert response.status_code == 302
    db.session.refresh(order)
    assert order.status is OrderStatus.PLACED and order.payment_method is PaymentMethod.CASH_ON_SITE
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "data-pay-panel" not in page and "پرداخت در محل" in page


def test_payment_buttons_do_nothing_for_other_orders(client, dish):
    place_cash = checkout_online(client, dish, payment_method="cash_on_site")
    order = db.session.query(Order).one()
    assert place_cash.status_code == 302 and order.status is OrderStatus.PLACED
    for action in ("start", "cash"):
        response = client.post(f"/fa/pay/{order.public_token}/{action}")
        assert response.status_code == 302
    db.session.refresh(order)
    assert order.payment_method is PaymentMethod.CASH_ON_SITE and len(order.payments) == 1
    assert client.post("/fa/pay/nope/start").status_code == 404


def test_the_callback_rejects_other_gateways_and_unknown_references(client, dish):
    assert client.get("/fa/pay/callback/zarinpal?authority=x&status=ok").status_code == 404
    response = client.get("/fa/pay/callback/mock?authority=MOCKA-nothing&status=ok")
    assert response.status_code == 302 and response.headers["Location"].endswith("/fa/menu")
    assert client.get("/fa/pay/callback/mock").status_code == 302


def test_replaying_a_callback_cannot_undo_a_payment(client, dish):
    authority = authority_of(checkout_online(client, dish))
    client.get(f"/fa/pay/callback/mock?authority={authority}&status=ok")
    client.get(f"/fa/pay/callback/mock?authority={authority}&status=failed")
    order = db.session.query(Order).one()
    assert order.is_paid and order.status is OrderStatus.PLACED and len(order.payments) == 1


def test_the_order_status_api_names_the_waiting_status(client, dish):
    checkout_online(client, dish, "en")
    order = db.session.query(Order).one()
    data = client.get(f"/api/orders/{order.public_token}/status?lang=en").get_json()
    assert data == {"status": "awaiting_payment", "label": "Waiting for payment", "final": False}


def test_the_demo_button_cannot_push_an_unpaid_order(app, client, dish):
    app.config["DEMO_MODE"] = True
    checkout_online(client, dish)
    order = db.session.query(Order).one()
    client.post(f"/fa/order/{order.public_token}/advance")
    db.session.refresh(order)
    assert order.status is OrderStatus.AWAITING_PAYMENT


# --- the admin panel -----------------------------------------------------------------------


def test_waiting_orders_stay_off_the_board_but_are_in_the_history(app, client, dish):
    checkout_online(client, dish)
    manager = staff_client(app, "manager")
    assert "data-order-id" not in manager.get("/admin/orders").get_data(as_text=True)
    history = manager.get("/admin/orders/history?status=awaiting_payment").get_data(as_text=True)
    assert "در انتظار پرداخت" in history and "/admin/orders/1" in history
    assert manager.get("/admin/dashboard").status_code == 200


def test_paid_online_orders_reach_the_board_with_a_test_chip(app, client, dish):
    authority = authority_of(checkout_online(client, dish))
    client.get(f"/fa/pay/callback/mock?authority={authority}&status=ok")
    manager = staff_client(app, "manager")
    board = manager.get("/admin/orders").get_data(as_text=True)
    assert "data-order-id" in board and "پرداخت‌شده · آزمایشی" in board


def test_order_detail_lists_attempts_with_transaction_ids_and_the_test_badge(app, client, dish):
    first = authority_of(checkout_online(client, dish))
    client.get(f"/fa/pay/callback/mock?authority={first}&status=failed")
    order = db.session.query(Order).one()
    second = authority_of(client.post(f"/fa/pay/{order.public_token}/start"))
    client.get(f"/fa/pay/callback/mock?authority={second}&status=ok")
    db.session.refresh(order)
    page = staff_client(app, "manager").get(f"/admin/orders/{order.id}").get_data(as_text=True)
    assert page.count("payments__item") >= 2
    assert order.latest_payment.transaction_id in page and "آزمایشی" in page
    assert "ناموفق" in page and "پرداخت‌شده" in page
    assert "دریافت وجه شد" not in page


def test_staff_record_cash_once_and_viewers_cannot(app, client, dish):
    checkout_online(client, dish, payment_method="cash_on_site")
    order = db.session.query(Order).one()
    manager = staff_client(app, "manager")
    assert "دریافت وجه شد" in manager.get(f"/admin/orders/{order.id}").get_data(as_text=True)
    assert staff_client(app, "viewer").post(f"/admin/orders/{order.id}/paid").status_code == 403
    db.session.refresh(order)
    assert not order.is_paid
    assert manager.post(f"/admin/orders/{order.id}/paid").status_code == 302
    db.session.refresh(order)
    assert order.is_paid
    page = manager.get(f"/admin/orders/{order.id}").get_data(as_text=True)
    assert "دریافت وجه شد" not in page
    again = manager.post(f"/admin/orders/{order.id}/paid", follow_redirects=True)
    assert "قابل ثبت نیست" in again.get_data(as_text=True)


def test_cash_cannot_be_recorded_on_a_waiting_online_order(app, client, dish):
    checkout_online(client, dish)
    order = db.session.query(Order).one()
    manager = staff_client(app, "manager")
    assert "دریافت وجه شد" not in manager.get(f"/admin/orders/{order.id}").get_data(as_text=True)
    manager.post(f"/admin/orders/{order.id}/paid")
    db.session.refresh(order)
    assert not order.is_paid


def test_the_kitchen_sees_payment_chips_but_no_amounts(app, client, dish):
    checkout_online(client, dish, payment_method="cash_on_site")
    page = staff_client(app, "kitchen").get("/admin/orders").get_data(as_text=True)
    assert "وجه در محل" in page and "280" not in page


def test_waiting_orders_are_not_counted_as_sales(app, client, dish):
    from restaurant.service_factory import make_dashboard_service

    authority = authority_of(checkout_online(client, dish))
    data = make_dashboard_service().today()
    assert data.orders_today == 0 and data.sales_today == 0
    client.get(f"/fa/pay/callback/mock?authority={authority}&status=ok")
    data = make_dashboard_service().today()
    assert data.orders_today == 1 and data.sales_today == 280_000


def test_customer_totals_leave_out_unpaid_online_orders(app, client, dish):
    from restaurant.service_factory import make_order_service as orders
    from tests.helpers import make_customer

    customer = make_customer()
    for method in (PaymentMethod.ONLINE, PaymentMethod.CASH_ON_SITE):
        order = place(dish, method)
        order.user_id = customer.id
    db.session.commit()
    stats = orders()._order_repository.stats_for_users([customer.id])
    assert stats[customer.id].order_count == 1 and stats[customer.id].total_spent == 280_000
