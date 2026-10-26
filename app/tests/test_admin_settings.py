"""The admin Settings page: ordering pause, delivery fee, payment methods and contact details."""

import pytest

from restaurant.constants import FulfillmentType, PaymentMethod
from restaurant.extensions import db
from restaurant.models import Order
from restaurant.service_factory import make_site_settings_service
from restaurant.services import OrderingSettings
from tests.helpers import add_category, add_dish, staff_client

VALID_CHECKOUT = {
    "customer_name": "علی رضایی",
    "customer_phone": "09123456789",
    "fulfillment": "takeaway",
    "delivery_address": "",
    "note": "",
    "payment_method": "cash_on_site",
}


def settings_form(**changes) -> dict[str, str]:
    """Return a complete valid settings form; `changes` replace single values."""
    form = {
        "delivery_fee": "30000",
        "cash_payment": "y",
        "online_payment": "y",
        "pause_message_fa": "",
        "pause_message_en": "",
        "phone": "021-12345678",
        "address_fa": "تهران",
        "address_en": "Tehran",
        "hours_fa": "هر روز ۱۲ تا ۲۳",
        "hours_en": "Daily 12 to 23",
    }
    form.update(changes)
    return {key: value for key, value in form.items() if value is not None}


@pytest.fixture
def dish_id(app) -> int:
    category = add_category("a", {"fa": "الف", "en": "A"})
    kebab = add_dish(category, {"fa": "کباب", "en": "Kebab"}, base_price=280_000)
    db.session.commit()
    return kebab.id


def save(client, **changes):
    return client.post("/admin/settings", data=settings_form(**changes))


def test_manager_sees_and_saves_the_settings(app) -> None:
    client = staff_client(app, "manager")
    assert client.get("/admin/settings").status_code == 200
    response = save(client, delivery_fee="45000", phone="09121112233")
    assert response.status_code == 302
    assert make_site_settings_service().get_delivery_fee() == 45_000
    page = client.get("/admin/settings").get_data(as_text=True)
    assert "45000" in page and "09121112233" in page


def test_the_untouched_page_can_be_saved_with_its_placeholder_texts(app) -> None:
    import re

    client = staff_client(app, "manager")
    page = client.get("/admin/settings").get_data(as_text=True)
    form = {
        name: value
        for name, value in re.findall(r'name="(\w+)"[^>]*? value="([^"]*)"', page)
        if name != "csrf_token"
    }
    form |= {"cash_payment": "y", "online_payment": "y"}
    assert client.post("/admin/settings", data=form).status_code == 302


def test_viewer_can_look_but_not_save(app) -> None:
    client = staff_client(app, "viewer")
    assert client.get("/admin/settings").status_code == 200
    assert save(client, delivery_fee="1").status_code == 403
    assert make_site_settings_service().get_delivery_fee() == 30_000


def test_roles_without_the_permission_get_403(app) -> None:
    assert staff_client(app, "cashier").get("/admin/settings").status_code == 403


def test_the_sidebar_links_to_both_new_sections(app) -> None:
    page = staff_client(app, "manager").get("/admin/dashboard").get_data(as_text=True)
    assert 'href="/admin/settings"' in page and 'href="/admin/site"' in page


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"delivery_fee": "-5"}, "هزینه‌ی ارسال"),
        ({"delivery_fee": "99999999999"}, "هزینه‌ی ارسال"),
        ({"delivery_fee": "abc"}, ""),
        ({"cash_payment": None, "online_payment": None}, "دست‌کم یک روش پرداخت"),
        ({"phone": "call me <b>"}, "شماره‌ی تماس"),
        ({"address_fa": "x" * 201}, "بیش از حد طولانی"),
    ],
)
def test_bad_values_are_refused_with_a_message_and_nothing_changes(app, changes, message) -> None:
    client = staff_client(app, "manager")
    response = save(client, **changes)
    assert response.status_code == 422
    assert message in response.get_data(as_text=True)
    assert make_site_settings_service().get_delivery_fee() == 30_000


def test_delivery_fee_reaches_the_order_total(app, dish_id) -> None:
    save(staff_client(app, "manager"), delivery_fee="50000")
    shopper = app.test_client()
    shopper.post("/api/cart/add", json={"dish_id": dish_id, "quantity": 1})
    form = {
        **VALID_CHECKOUT,
        "fulfillment": "delivery",
        "delivery_address": "تهران، خیابان آزادی، پلاک ۱۲",
    }
    shopper.post("/fa/checkout", data=form)
    order = db.session.query(Order).one()
    assert order.fulfillment is FulfillmentType.DELIVERY
    assert (order.delivery_fee, order.total) == (50_000, 330_000)


def test_contact_texts_show_in_the_footer_in_both_languages(app) -> None:
    save(staff_client(app, "manager"), address_fa="تهران، میدان تجریش", address_en="Tajrish Square")
    visitor = app.test_client()
    assert "میدان تجریش" in visitor.get("/fa/").get_data(as_text=True)
    assert "Tajrish Square" in visitor.get("/en/").get_data(as_text=True)


class TestPause:
    """Pausing stops new orders everywhere but leaves existing ones and booking alone."""

    def pause(self, app) -> None:
        save(staff_client(app, "manager"), ordering_paused="y", pause_message_fa="امشب تعطیلیم")

    def test_pause_bar_shows_with_the_custom_message(self, app) -> None:
        self.pause(app)
        assert "امشب تعطیلیم" in app.test_client().get("/fa/menu").get_data(as_text=True)
        english = app.test_client().get("/en/menu").get_data(as_text=True)
        assert "Online ordering is paused" in english

    def test_no_bar_when_not_paused(self, app) -> None:
        assert 'class="pause-bar"' not in app.test_client().get("/fa/menu").get_data(as_text=True)

    def test_cart_api_refuses_additions(self, app, dish_id) -> None:
        self.pause(app)
        shopper = app.test_client()
        response = shopper.post("/api/cart/add", json={"dish_id": dish_id, "quantity": 1})
        assert response.status_code == 409
        assert shopper.get("/api/cart").get_json()["count"] == 0

    def test_checkout_sends_the_visitor_back_to_the_cart(self, app, dish_id) -> None:
        shopper = app.test_client()
        shopper.post("/api/cart/add", json={"dish_id": dish_id, "quantity": 1})
        self.pause(app)
        response = shopper.post("/fa/checkout", data=VALID_CHECKOUT)
        assert response.status_code == 302 and response.headers["Location"].endswith("/fa/cart")
        assert db.session.query(Order).count() == 0

    def test_reservation_page_still_opens(self, app) -> None:
        self.pause(app)
        assert app.test_client().get("/fa/reserve").status_code == 200

    def test_resuming_lets_orders_through_again(self, app, dish_id) -> None:
        manager = staff_client(app, "manager")
        save(manager, ordering_paused="y")
        save(manager)
        response = app.test_client().post("/api/cart/add", json={"dish_id": dish_id, "quantity": 1})
        assert response.status_code == 200


class TestPaymentMethods:
    """The two payment switches decide what checkout offers."""

    def checkout_page(self, app, dish_id) -> str:
        shopper = app.test_client()
        shopper.post("/api/cart/add", json={"dish_id": dish_id, "quantity": 1})
        return shopper.get("/fa/checkout").get_data(as_text=True)

    def test_both_methods_are_offered_by_default(self, app, dish_id) -> None:
        page = self.checkout_page(app, dish_id)
        assert 'value="cash_on_site"' in page and 'value="online"' in page

    def test_switching_online_off_removes_it_and_refuses_it(self, app, dish_id) -> None:
        save(staff_client(app, "manager"), online_payment=None)
        assert 'value="online"' not in self.checkout_page(app, dish_id)
        shopper = app.test_client()
        shopper.post("/api/cart/add", json={"dish_id": dish_id, "quantity": 1})
        shopper.post("/fa/checkout", data={**VALID_CHECKOUT, "payment_method": "online"})
        assert db.session.query(Order).count() == 0

    def test_switching_cash_off_leaves_only_online(self, app, dish_id) -> None:
        save(staff_client(app, "manager"), cash_payment=None)
        page = self.checkout_page(app, dish_id)
        assert 'value="cash_on_site"' not in page and 'value="online"' in page

    def test_settings_are_stored_as_a_value_object(self, app) -> None:
        save(staff_client(app, "manager"), delivery_fee="0", online_payment=None)
        assert make_site_settings_service().get_ordering_settings() == OrderingSettings(
            delivery_fee=0, online_payment=False, cash_payment=True, paused=False
        )
        assert PaymentMethod.CASH_ON_SITE.value == "cash_on_site"
