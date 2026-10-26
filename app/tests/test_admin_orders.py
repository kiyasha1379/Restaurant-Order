"""The orders section of the panel: board, list, detail, actions, receipt and money hiding."""

from datetime import timedelta

import pytest

from restaurant.constants import FulfillmentType, OrderStatus, PaymentMethod
from restaurant.extensions import db
from restaurant.models import Order, OrderItem, OrderItemOption, OrderStatusLog
from restaurant.order_stream import ChangeStream
from restaurant.timeutils import now_tehran
from tests.helpers import staff_client

SECRET_NAME = "Zahra Secret-Customer"
SECRET_PHONE = "09120000000"


def add_order(
    status: OrderStatus = OrderStatus.PLACED,
    fulfillment: FulfillmentType = FulfillmentType.TAKEAWAY,
    total: int = 250_000,
    note: str = "",
    created_at=None,
) -> Order:
    order = Order(
        public_token=f"tok{db.session.query(Order).count()}",
        language_code="fa",
        customer_name=SECRET_NAME,
        customer_phone=SECRET_PHONE,
        fulfillment=fulfillment,
        delivery_address=(
            "Tehran, Some Street 12" if fulfillment is FulfillmentType.DELIVERY else ""
        ),
        note=note,
        payment_method=PaymentMethod.CASH_ON_SITE,
        status=status,
        subtotal=total,
        delivery_fee=0,
        total=total,
        items=[
            OrderItem(
                name_fa="پیتزا مارگاریتا",
                name_en="Margherita pizza",
                unit_price=total,
                quantity=1,
                line_total=total,
                options=[OrderItemOption(name_fa="پنیر اضافه", name_en="Extra cheese", price=0)],
            )
        ],
        status_log=[OrderStatusLog(from_status=None, to_status=OrderStatus.PLACED)],
    )
    if created_at is not None:
        order.created_at = created_at
    db.session.add(order)
    db.session.commit()
    return order


def test_board_puts_orders_in_their_columns(app) -> None:
    add_order(OrderStatus.PLACED)
    add_order(OrderStatus.PREPARING)
    add_order(OrderStatus.READY)
    add_order(OrderStatus.OUT_FOR_DELIVERY, FulfillmentType.DELIVERY)
    add_order(OrderStatus.CANCELLED)
    old = add_order(OrderStatus.COMPLETED, created_at=now_tehran() - timedelta(days=2))
    today_done = add_order(OrderStatus.COMPLETED)
    client = staff_client(app, "cashier")
    page = client.get("/admin/orders").get_data(as_text=True)
    columns = page.split('class="board__column ')[1:]
    assert len(columns) == 4
    for column, expected in zip(columns, (1, 1, 2, 1), strict=True):
        assert column.count('data-order-id="') == expected
    assert f'data-order-id="{old.id}"' not in page
    assert f'data-order-id="{today_done.id}"' in page


def test_kitchen_sees_items_and_note_but_no_money_or_customer(app) -> None:
    add_order(note="no onions please", total=987_000)
    client = staff_client(app, "kitchen")
    for path in (
        "/admin/orders",
        "/admin/orders/1",
        "/admin/orders/1/receipt",
        "/admin/orders/board",
    ):
        page = client.get(path).get_data(as_text=True)
        assert "پیتزا مارگاریتا" in page and "no onions please" in page, path
        assert SECRET_NAME not in page and SECRET_PHONE not in page, path
        assert "۹۸۷٬۰۰۰" not in page, path


def test_cashier_sees_amounts_and_customer(app) -> None:
    add_order(total=987_000)
    client = staff_client(app, "cashier")
    for path in ("/admin/orders", "/admin/orders/1", "/admin/orders/1/receipt"):
        page = client.get(path).get_data(as_text=True)
        assert SECRET_NAME in page and "۹۸۷٬۰۰۰" in page, path
    assert SECRET_PHONE in client.get("/admin/orders/1").get_data(as_text=True)


def test_viewer_sees_orders_but_has_no_buttons_and_cannot_post(app) -> None:
    order = add_order()
    client = staff_client(app, "viewer")
    board = client.get("/admin/orders").get_data(as_text=True)
    assert "پیتزا مارگاریتا" in board
    assert "/advance" not in board and "/cancel" not in board
    assert "/advance" not in client.get(f"/admin/orders/{order.id}").get_data(as_text=True)
    assert client.post(f"/admin/orders/{order.id}/advance").status_code == 403
    assert client.post(f"/admin/orders/{order.id}/cancel").status_code == 403
    assert db.session.get(Order, order.id).status is OrderStatus.PLACED


def test_visitors_cannot_post_actions(app, client) -> None:
    order = add_order()
    assert client.post(f"/admin/orders/{order.id}/advance").status_code == 302
    assert db.session.get(Order, order.id).status is OrderStatus.PLACED


def test_advance_walks_a_delivery_order_to_the_end_and_logs_who(app) -> None:
    order = add_order(fulfillment=FulfillmentType.DELIVERY)
    client = staff_client(app, "cashier")
    seen = []
    for _ in range(4):
        response = client.post(f"/admin/orders/{order.id}/advance")
        assert response.status_code == 302
        seen.append(db.session.get(Order, order.id).status)
    assert seen == [
        OrderStatus.PREPARING,
        OrderStatus.READY,
        OrderStatus.OUT_FOR_DELIVERY,
        OrderStatus.COMPLETED,
    ]
    log = db.session.get(Order, order.id).status_log
    assert [entry.to_status for entry in log][-1] is OrderStatus.COMPLETED
    assert all(entry.changed_by_user_id for entry in log[1:])
    # A finished order cannot move on: the page says so instead of failing.
    again = client.post(f"/admin/orders/{order.id}/advance", follow_redirects=True)
    assert "اکنون ممکن نیست" in again.get_data(as_text=True)


def test_takeaway_skips_the_delivery_status(app) -> None:
    order = add_order()
    client = staff_client(app, "kitchen")
    for _ in range(3):
        client.post(f"/admin/orders/{order.id}/advance")
    assert db.session.get(Order, order.id).status is OrderStatus.COMPLETED


def test_cancel_works_until_completed(app) -> None:
    open_order, done_order = add_order(), add_order(OrderStatus.COMPLETED)
    client = staff_client(app, "cashier")
    client.post(f"/admin/orders/{open_order.id}/cancel")
    client.post(f"/admin/orders/{done_order.id}/cancel")
    assert db.session.get(Order, open_order.id).status is OrderStatus.CANCELLED
    assert db.session.get(Order, done_order.id).status is OrderStatus.COMPLETED


def test_action_redirects_only_to_panel_addresses(app) -> None:
    order = add_order()
    client = staff_client(app, "cashier")
    ok = client.post(f"/admin/orders/{order.id}/advance", data={"next": "/admin/orders"})
    assert ok.headers["Location"] == "/admin/orders"
    evil = client.post(f"/admin/orders/{order.id}/advance", data={"next": "https://evil.example/"})
    assert evil.headers["Location"] == f"/admin/orders/{order.id}"


def test_unknown_order_is_404(app) -> None:
    client = staff_client(app, "admin")
    assert client.get("/admin/orders/999").status_code == 404
    assert client.get("/admin/orders/999/receipt").status_code == 404
    assert client.post("/admin/orders/999/advance").status_code == 404


def test_history_filters_and_search(app) -> None:
    add_order(OrderStatus.COMPLETED)
    add_order(OrderStatus.CANCELLED, FulfillmentType.DELIVERY)
    add_order(OrderStatus.PLACED)
    client = staff_client(app, "cashier")
    page = client.get("/admin/orders/history").get_data(as_text=True)
    assert "۳ سفارش" in page
    assert "۱ سفارش" in client.get("/admin/orders/history?status=cancelled").get_data(as_text=True)
    assert "۱ سفارش" in client.get("/admin/orders/history?fulfillment=delivery").get_data(
        as_text=True
    )
    assert "۳ سفارش" in client.get("/admin/orders/history?q=Zahra").get_data(as_text=True)
    assert "۱ سفارش" in client.get("/admin/orders/history?q=3").get_data(as_text=True)
    assert "۰ سفارش" in client.get("/admin/orders/history?q=nobody-by-this-name").get_data(
        as_text=True
    )
    # A bad filter value is ignored.
    assert "۳ سفارش" in client.get("/admin/orders/history?status=bogus&fulfillment=x").get_data(
        as_text=True
    )


def test_search_is_ignored_without_the_money_permission(app) -> None:
    add_order()
    client = staff_client(app, "kitchen")
    page = client.get("/admin/orders/history?q=nobody-by-this-name").get_data(as_text=True)
    assert "۱ سفارش" in page and SECRET_NAME not in page


def test_history_paginates(app) -> None:
    for _ in range(23):
        add_order(OrderStatus.COMPLETED)
    client = staff_client(app, "cashier")
    first = client.get("/admin/orders/history").get_data(as_text=True)
    second = client.get("/admin/orders/history?page=2").get_data(as_text=True)
    assert first.count('class="table__num">#') == 20
    assert second.count('class="table__num">#') == 3
    assert "۲۳ سفارش" in first


def test_sidebar_badge_counts_orders_waiting_for_acceptance(app) -> None:
    add_order(OrderStatus.PLACED)
    add_order(OrderStatus.PLACED)
    add_order(OrderStatus.PREPARING)
    page = staff_client(app, "cashier").get("/admin/dashboard").get_data(as_text=True)
    assert '<span class="admin-nav__badge">۲</span>' in page


def test_dashboard_numbers(app) -> None:
    add_order(total=100_000)
    add_order(total=300_000)
    add_order(OrderStatus.CANCELLED, total=900_000)
    add_order(created_at=now_tehran() - timedelta(days=3), total=700_000)
    page = staff_client(app, "manager").get("/admin/dashboard").get_data(as_text=True)
    assert "۴۰۰٬۰۰۰" in page  # sales today without the cancelled and the old order
    assert "۲۰۰٬۰۰۰" in page  # average
    assert "۹۰۰٬۰۰۰" not in page


def test_fragment_and_stream_need_the_orders_permission(app, client) -> None:
    assert client.get("/admin/orders/board").status_code == 302
    assert client.get("/admin/orders/stream").status_code == 302
    dash_only = staff_client(app, "viewer")
    assert dash_only.get("/admin/orders/board").status_code == 200


def test_stream_answers_as_event_stream(app) -> None:
    client = staff_client(app, "cashier")
    response = client.get("/admin/orders/stream")
    assert response.mimetype == "text/event-stream"
    assert response.get_data(as_text=True).startswith(": keepalive")


def test_change_stream_emits_only_when_something_changed() -> None:
    markers = iter(["a", "a", "b", "b", "c"])
    now = {"t": 0.0}

    def sleep(seconds: float) -> None:
        now["t"] += seconds

    stream = ChangeStream(lambda: next(markers), 1, 4, sleep=sleep, clock=lambda: now["t"])
    events = list(stream.events())
    assert events[0].startswith(": keepalive")
    kinds = ["board" if e.startswith("event: board") else "ping" for e in events[1:]]
    assert kinds == ["ping", "board", "ping", "board"]


@pytest.mark.parametrize("role", ["kitchen", "cashier"])
def test_orders_pages_use_the_panel_language(app, role) -> None:
    add_order()
    client = staff_client(app, role)
    client.get("/admin/language/en")
    page = client.get("/admin/orders").get_data(as_text=True)
    assert "Margherita pizza" in page and "Extra cheese" in page and "Live board" in page
