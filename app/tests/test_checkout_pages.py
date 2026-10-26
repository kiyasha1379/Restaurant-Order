"""Cart page, checkout, order tracking and the demo advance button."""

import pytest

from restaurant import create_app
from restaurant.constants import FulfillmentType, OrderStatus
from restaurant.extensions import db
from restaurant.models import Dish, Order
from tests.conftest import add_two_languages
from tests.helpers import add_category, add_dish

VALID_FORM = {
    "customer_name": "علی رضایی",
    "customer_phone": "۰۹۱۲۳۴۵۶۷۸۹",
    "fulfillment": "takeaway",
    "delivery_address": "",
    "note": "",
    "payment_method": "cash_on_site",
}


@pytest.fixture
def dish_ids(app):
    category = add_category("a", {"fa": "الف", "en": "A"})
    kebab = add_dish(category, {"fa": "کباب", "en": "Kebab"}, base_price=280_000)
    doogh = add_dish(category, {"fa": "دوغ", "en": "Doogh"}, base_price=35_000)
    db.session.commit()
    return kebab.id, doogh.id


def fill_cart(client, dish_ids, quantity=2):
    client.post("/api/cart/add", json={"dish_id": dish_ids[0], "quantity": quantity})
    client.post("/api/cart/add", json={"dish_id": dish_ids[1], "quantity": 1})


def only_order() -> Order:
    return db.session.query(Order).one()


def test_cart_page_has_the_panel_and_a_checkout_link(client):
    html = client.get("/fa/cart").get_data(as_text=True)
    assert "data-cart-panel" in html and "/fa/checkout" in html


def test_checkout_with_an_empty_cart_goes_back_to_the_cart(client):
    response = client.get("/fa/checkout")
    assert response.status_code == 302 and response.headers["Location"].endswith("/fa/cart")


def test_checkout_page_shows_the_summary_in_both_languages(client, dish_ids):
    fill_cart(client, dish_ids)
    persian = client.get("/fa/checkout").get_data(as_text=True)
    english = client.get("/en/checkout").get_data(as_text=True)
    assert "کباب" in persian and "۵۹۵٬۰۰۰" in persian
    assert "Kebab" in english and "595,000" in english and 'dir="ltr"' in english


def test_valid_takeaway_order_is_placed_and_the_cart_emptied(client, dish_ids):
    fill_cart(client, dish_ids)
    response = client.post("/fa/checkout", data=VALID_FORM)
    assert response.status_code == 302
    order = only_order()
    assert response.headers["Location"].endswith(f"/fa/order/{order.public_token}")
    assert (order.subtotal, order.delivery_fee, order.total) == (595_000, 0, 595_000)
    assert order.customer_phone == "09123456789" and order.language_code == "fa"
    assert order.status is OrderStatus.PLACED
    assert client.get("/api/cart").get_json()["count"] == 0


def test_delivery_order_stores_address_and_fee(client, dish_ids):
    fill_cart(client, dish_ids, quantity=1)
    form = {
        **VALID_FORM,
        "fulfillment": "delivery",
        "delivery_address": "تهران، خیابان آزادی، پلاک ۱۲",
    }
    client.post("/fa/checkout", data=form)
    order = only_order()
    assert order.fulfillment is FulfillmentType.DELIVERY
    assert order.delivery_fee == 30_000 and order.total == 315_000 + 30_000
    assert "آزادی" in order.delivery_address


def test_a_price_sent_by_the_browser_is_ignored(client, dish_ids):
    fill_cart(client, dish_ids, quantity=1)
    client.post("/fa/checkout", data={**VALID_FORM, "total": "1", "subtotal": "1"})
    assert only_order().total == 315_000


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"customer_name": " "}, "نام را وارد کنید"),
        ({"customer_phone": "123"}, "شماره‌ی موبایل معتبر نیست"),
        ({"fulfillment": "delivery", "delivery_address": "کوتاه"}, "آدرس را کامل وارد کنید"),
        ({"note": "x" * 501}, "توضیحات بیش از حد طولانی"),
    ],
)
def test_invalid_checkout_shows_a_persian_error_and_places_nothing(
    client, dish_ids, changes, message
):
    fill_cart(client, dish_ids)
    response = client.post("/fa/checkout", data={**VALID_FORM, **changes})
    assert response.status_code == 200 and message in response.get_data(as_text=True)
    assert db.session.query(Order).count() == 0
    assert client.get("/api/cart").get_json()["count"] == 3


def test_error_messages_are_english_on_the_english_page(client, dish_ids):
    fill_cart(client, dish_ids)
    html = client.post("/en/checkout", data={**VALID_FORM, "customer_phone": "1"}).get_data(
        as_text=True
    )
    assert "not a valid mobile number" in html


def test_unknown_fulfillment_choice_is_rejected(client, dish_ids):
    fill_cart(client, dish_ids)
    client.post("/fa/checkout", data={**VALID_FORM, "fulfillment": "teleport"})
    assert db.session.query(Order).count() == 0


def test_dish_that_sells_out_during_checkout_is_removed_and_reported(client, dish_ids):
    fill_cart(client, dish_ids)
    db.session.get(Dish, dish_ids[1]).is_in_stock = False
    db.session.commit()
    response = client.post("/fa/checkout", data=VALID_FORM, follow_redirects=True)
    assert db.session.query(Order).count() == 0
    assert "دیگر موجود نیست" in response.get_data(as_text=True)
    assert client.get("/api/cart").get_json()["count"] == 2


def test_order_page_shows_items_totals_and_status(client, dish_ids):
    fill_cart(client, dish_ids)
    client.post("/fa/checkout", data=VALID_FORM)
    token = only_order().public_token
    persian = client.get(f"/fa/order/{token}").get_data(as_text=True)
    assert "کباب" in persian and "۵۹۵٬۰۰۰" in persian and "ثبت شد" in persian
    english = client.get(f"/en/order/{token}").get_data(as_text=True)
    assert "Kebab" in english and "Placed" in english and "595,000" in english


def test_order_page_rejects_unknown_tokens(client):
    assert client.get("/fa/order/not-a-real-token").status_code == 404


def test_order_page_is_not_reachable_by_the_numeric_id(client, dish_ids):
    fill_cart(client, dish_ids)
    client.post("/fa/checkout", data=VALID_FORM)
    assert client.get(f"/fa/order/{only_order().id}").status_code == 404


def test_demo_button_is_only_there_in_demo_mode(client, dish_ids):
    fill_cart(client, dish_ids)
    client.post("/fa/checkout", data=VALID_FORM)
    token = only_order().public_token
    assert "/advance" not in client.get(f"/fa/order/{token}").get_data(as_text=True)
    assert client.post(f"/fa/order/{token}/advance").status_code == 404


def test_demo_advance_moves_the_order_forward():
    app = create_app("demo", {"SQLALCHEMY_DATABASE_URI": "sqlite://", "WTF_CSRF_ENABLED": False})
    with app.app_context():
        db.create_all()
        add_two_languages()
        category = add_category("a", {"fa": "الف"})
        dish = add_dish(category, {"fa": "کباب"}, base_price=1000)
        db.session.commit()
        client = app.test_client()
        client.post("/api/cart/add", json={"dish_id": dish.id})
        client.post("/fa/checkout", data=VALID_FORM)
        token = only_order().public_token
        assert "/advance" in client.get(f"/fa/order/{token}").get_data(as_text=True)
        client.post(f"/fa/order/{token}/advance")
        db.session.expire_all()
        assert only_order().status is OrderStatus.PREPARING
        for _ in range(5):
            client.post(f"/fa/order/{token}/advance")
        db.session.expire_all()
        assert only_order().status is OrderStatus.COMPLETED
        assert "/advance" not in client.get(f"/fa/order/{token}").get_data(as_text=True)
        db.drop_all()


def test_status_endpoint_and_stream_report_the_status(client, dish_ids):
    fill_cart(client, dish_ids)
    client.post("/fa/checkout", data=VALID_FORM)
    order = only_order()
    status = client.get(f"/api/orders/{order.public_token}/status?lang=en").get_json()
    assert status == {"status": "placed", "label": "Placed", "final": False}
    stream = client.get(f"/api/orders/{order.public_token}/stream?lang=fa")
    assert stream.mimetype == "text/event-stream"
    body = stream.get_data(as_text=True)
    assert body.startswith("event: status") and "ثبت شد" in body


def test_stream_and_status_return_404_for_unknown_tokens(client):
    assert client.get("/api/orders/nope/status").status_code == 404
    assert client.get("/api/orders/nope/stream").status_code == 404


def test_pages_carry_the_csrf_token_and_script_config(client):
    html = client.get("/fa/").get_data(as_text=True)
    assert 'name="csrf-token"' in html
    assert 'id="site-config"' in html and "/api/cart/add" in html
