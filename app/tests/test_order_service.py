"""Pricing and ordering rules, against a real in-memory database."""

import pytest

from restaurant.constants import FulfillmentType, OrderStatus, PaymentMethod
from restaurant.extensions import db
from restaurant.models import Dish, Order, Setting
from restaurant.service_factory import make_order_service, make_pricing_service
from restaurant.services import (
    CartLine,
    EmptyCartError,
    InvalidTransitionError,
    PlaceOrderRequest,
    UnavailableDishError,
)
from tests.helpers import add_category, add_dish

DELIVERY_FEE = 30_000


@pytest.fixture
def dishes(app):
    category = add_category("a", {"fa": "الف", "en": "A"})
    first = add_dish(category, {"fa": "کباب", "en": "Kebab"}, base_price=280_000)
    second = add_dish(category, {"fa": "دوغ", "en": "Doogh"}, base_price=35_000)
    db.session.commit()
    return first, second


def lines(*pairs):
    return [CartLine(f"dish-{dish.id}", dish.id, quantity) for dish, quantity in pairs]


def request_for(fulfillment=FulfillmentType.TAKEAWAY, **fields):
    values = {
        "customer_name": "Ali",
        "customer_phone": "09123456789",
        "fulfillment": fulfillment,
        "delivery_address": "Tehran, Azadi street 12",
        "note": "",
        "payment_method": PaymentMethod.CASH_ON_SITE,
        "language_code": "fa",
    }
    return PlaceOrderRequest(**{**values, **fields})


def test_lines_are_priced_from_the_menu(dishes):
    kebab, doogh = dishes
    priced = make_pricing_service().price(
        lines((kebab, 2), (doogh, 3)), FulfillmentType.TAKEAWAY, "fa"
    )
    assert [line.line_total for line in priced.lines] == [560_000, 105_000]
    assert priced.subtotal == 665_000 and priced.delivery_fee == 0 and priced.total == 665_000


def test_delivery_adds_the_fixed_fee(dishes):
    kebab, _ = dishes
    priced = make_pricing_service().price(lines((kebab, 1)), FulfillmentType.DELIVERY, "fa")
    assert priced.delivery_fee == DELIVERY_FEE
    assert priced.total == 280_000 + DELIVERY_FEE


def test_delivery_fee_comes_from_the_settings(dishes):
    kebab, _ = dishes
    db.session.add(Setting(key="delivery_fee", value="45000"))
    db.session.commit()
    priced = make_pricing_service().price(lines((kebab, 1)), FulfillmentType.DELIVERY, "fa")
    assert priced.delivery_fee == 45_000


@pytest.mark.parametrize("broken", ["abc", "-5", ""])
def test_a_broken_fee_setting_uses_the_default(dishes, broken):
    kebab, _ = dishes
    db.session.add(Setting(key="delivery_fee", value=broken))
    db.session.commit()
    priced = make_pricing_service().price(lines((kebab, 1)), FulfillmentType.DELIVERY, "fa")
    assert priced.delivery_fee == DELIVERY_FEE


def test_names_follow_the_language_and_keep_both_for_the_snapshot(dishes):
    kebab, _ = dishes
    english = make_pricing_service().price(lines((kebab, 1)), FulfillmentType.TAKEAWAY, "en")
    line = english.lines[0]
    assert (line.name, line.name_fa, line.name_en) == ("Kebab", "کباب", "Kebab")


def test_an_empty_cart_has_no_delivery_fee(app):
    priced = make_pricing_service().price([], FulfillmentType.DELIVERY, "fa")
    assert priced.total == 0 and priced.lines == []


def test_hidden_sold_out_and_missing_dishes_are_not_priced(dishes):
    kebab, doogh = dishes
    kebab.is_visible = False
    doogh.is_in_stock = False
    db.session.commit()
    cart = lines((kebab, 1), (doogh, 1)) + [CartLine("dish-999", 999, 1)]
    priced = make_pricing_service().price(cart, FulfillmentType.TAKEAWAY, "fa")
    assert priced.lines == [] and priced.total == 0
    assert priced.unavailable_line_ids == {f"dish-{kebab.id}", f"dish-{doogh.id}", "dish-999"}


def test_stored_order_equals_the_server_calculation(dishes):
    kebab, doogh = dishes
    cart = lines((kebab, 2), (doogh, 1))
    service = make_order_service()
    expected = make_pricing_service().price(cart, FulfillmentType.DELIVERY, "fa")
    order = service.place_order(request_for(FulfillmentType.DELIVERY), cart)
    db.session.commit()
    stored = db.session.get(Order, order.id)
    assert (stored.subtotal, stored.delivery_fee, stored.total) == (
        expected.subtotal,
        expected.delivery_fee,
        expected.total,
    )
    assert sum(item.line_total for item in stored.items) == stored.subtotal
    assert stored.total == stored.subtotal + stored.delivery_fee


def test_order_lines_are_snapshots(dishes):
    kebab, _ = dishes
    order = make_order_service().place_order(request_for(), lines((kebab, 2)))
    db.session.commit()
    kebab.base_price = 999_999
    db.session.commit()
    item = db.session.get(Order, order.id).items[0]
    assert (item.unit_price, item.line_total, item.name_fa, item.name_en) == (
        280_000,
        560_000,
        "کباب",
        "Kebab",
    )
    assert item.name_in("en") == "Kebab" and item.name_in("fa") == "کباب"


def test_order_snapshot_survives_deleting_the_dish(dishes):
    kebab, _ = dishes
    order = make_order_service().place_order(request_for(), lines((kebab, 1)))
    db.session.commit()
    db.session.delete(db.session.get(Dish, kebab.id))
    db.session.commit()
    item = db.session.get(Order, order.id).items[0]
    assert item.dish_id is None and item.name_fa == "کباب"


def test_new_order_starts_placed_with_one_log_entry_and_a_token(dishes):
    kebab, _ = dishes
    order = make_order_service().place_order(request_for(), lines((kebab, 1)))
    db.session.commit()
    assert order.status is OrderStatus.PLACED
    assert [(log.from_status, log.to_status) for log in order.status_log] == [
        (None, OrderStatus.PLACED)
    ]
    assert len(order.public_token) >= 12 and order.number == order.id


def test_tokens_differ_between_orders(dishes):
    kebab, _ = dishes
    service = make_order_service()
    tokens = {service.place_order(request_for(), lines((kebab, 1))).public_token for _ in range(5)}
    assert len(tokens) == 5


def test_takeaway_orders_keep_no_address_and_no_fee(dishes):
    kebab, _ = dishes
    order = make_order_service().place_order(request_for(), lines((kebab, 1)))
    assert order.delivery_address == "" and order.delivery_fee == 0


def test_empty_cart_cannot_be_ordered(app):
    with pytest.raises(EmptyCartError):
        make_order_service().place_order(request_for(), [])


def test_unavailable_dish_stops_the_order_and_is_reported(dishes):
    kebab, doogh = dishes
    doogh.is_in_stock = False
    db.session.commit()
    with pytest.raises(UnavailableDishError) as error:
        make_order_service().place_order(request_for(), lines((kebab, 1), (doogh, 1)))
    assert error.value.line_ids == {f"dish-{doogh.id}"}
    assert db.session.query(Order).count() == 0


def test_changing_status_is_logged_and_rules_are_enforced(dishes):
    kebab, _ = dishes
    service = make_order_service()
    order = service.place_order(request_for(), lines((kebab, 1)))
    db.session.commit()
    service.change_status(order, OrderStatus.PREPARING, changed_by_user_id=None)
    assert order.status is OrderStatus.PREPARING
    assert order.status_log[-1].from_status is OrderStatus.PLACED
    with pytest.raises(InvalidTransitionError):
        service.change_status(order, OrderStatus.COMPLETED)
    assert order.status is OrderStatus.PREPARING


@pytest.mark.parametrize(
    ("fulfillment", "expected_path"),
    [
        (FulfillmentType.TAKEAWAY, ["preparing", "ready", "completed"]),
        (FulfillmentType.DELIVERY, ["preparing", "ready", "out_for_delivery", "completed"]),
    ],
)
def test_advance_walks_the_normal_path_then_stops(dishes, fulfillment, expected_path):
    kebab, _ = dishes
    service = make_order_service()
    order = service.place_order(request_for(fulfillment), lines((kebab, 1)))
    reached = []
    while True:
        try:
            service.advance(order)
        except InvalidTransitionError:
            break
        reached.append(order.status.value)
    assert reached == expected_path


def test_read_status_sees_changes_made_elsewhere(dishes):
    kebab, _ = dishes
    service = make_order_service()
    order = service.place_order(request_for(), lines((kebab, 1)))
    db.session.commit()
    db.session.execute(db.text("update orders set status='ready' where id=:id"), {"id": order.id})
    assert service.read_status(order.id) is OrderStatus.READY
