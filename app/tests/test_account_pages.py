"""The account area: orders and ordering again, bookings, addresses, profile, the saved cart."""

from datetime import datetime, timedelta

import pytest

from restaurant.constants import ReservationStatus
from restaurant.extensions import db
from restaurant.models import Address, BuilderOption, Dish, Order, Reservation, User
from tests.helpers import (
    CUSTOMER_PASSWORD,
    add_builder,
    add_category,
    add_dish,
    add_tables,
    customer_client,
    customer_sign_in,
    make_customer,
    option_ids,
)

CHECKOUT = {
    "customer_name": "Sara",
    "customer_phone": "09121234567",
    "fulfillment": "takeaway",
    "delivery_address": "",
    "note": "",
    "payment_method": "cash_on_site",
}


@pytest.fixture
def dishes(app):
    category = add_category("a", {"fa": "الف", "en": "A"})
    kebab = add_dish(category, {"fa": "کباب", "en": "Kebab"}, base_price=280_000)
    doogh = add_dish(category, {"fa": "دوغ", "en": "Doogh"}, base_price=35_000)
    db.session.commit()
    return kebab, doogh


def add_to_cart(client, dish, quantity=1):
    return client.post("/api/cart/add", json={"dish_id": dish.id, "quantity": quantity})


def cart_count(client) -> int:
    return client.get("/api/cart").get_json()["count"]


def place_order(client, dishes, **form):
    add_to_cart(client, dishes[0], 2)
    add_to_cart(client, dishes[1], 1)
    response = client.post("/fa/checkout", data={**CHECKOUT, **form})
    assert response.status_code == 302
    return db.session.query(Order).order_by(Order.id.desc()).first()


# --- guards and pages ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/account",
        "/account/orders",
        "/account/reservations",
        "/account/addresses",
        "/account/profile",
    ],
)
def test_guests_are_sent_to_sign_in_and_customers_see_every_page(app, path) -> None:
    guest = app.test_client()
    response = guest.get(f"/fa{path}")
    assert response.status_code == 302 and "/fa/login?next=/fa" in response.headers["Location"]
    client, _ = customer_client(app)
    for lang in ("fa", "en"):
        page = client.get(f"/{lang}{path}")
        assert page.status_code == 200
    assert 'dir="ltr"' in page.get_data(as_text=True)


def test_post_routes_need_a_signed_in_customer(app) -> None:
    guest = app.test_client()
    for path in (
        "/fa/account/addresses/1/delete",
        "/fa/account/addresses/1/default",
        "/fa/account/orders/abc/reorder",
        "/fa/account/password",
    ):
        assert guest.post(path).status_code == 302


def test_the_header_shows_sign_in_for_guests_and_the_account_for_customers(app) -> None:
    guest = app.test_client().get("/fa/").get_data(as_text=True)
    assert 'href="/fa/login"' in guest and "حساب من" not in guest
    client, _ = customer_client(app)
    assert "حساب من" in client.get("/fa/").get_data(as_text=True)


def test_the_overview_shows_orders_bookings_and_the_main_address(app, dishes) -> None:
    client, user = customer_client(app)
    order = place_order(client, dishes)
    db.session.add(
        Address(user_id=user.id, label="Home", text="Tehran, Azadi St 12", is_default=True)
    )
    db.session.commit()
    html = client.get("/fa/account").get_data(as_text=True)
    assert f"/fa/order/{order.public_token}" in html and "Tehran, Azadi St 12" in html
    assert "رزرو پیش‌رویی ندارید" in html


# --- orders ----------------------------------------------------------------------------------


def test_an_order_placed_while_signed_in_belongs_to_the_account(app, dishes) -> None:
    client, user = customer_client(app)
    order = place_order(client, dishes)
    assert order.user_id == user.id
    guest_order = place_order(app.test_client(), dishes)
    assert guest_order.user_id is None


def test_the_order_list_shows_only_my_orders_and_pages(app, dishes) -> None:
    client, _ = customer_client(app)
    mine = place_order(client, dishes)
    other, _ = customer_client(app, phone="09127654321", name="Other")
    theirs = place_order(other, dishes)
    html = client.get("/fa/account/orders").get_data(as_text=True)
    assert mine.public_token in html and theirs.public_token not in html
    assert client.get("/fa/account/orders?page=2").status_code == 200
    assert client.get("/fa/account/orders?page=abc").status_code == 200


def test_ordering_again_puts_the_lines_in_the_cart(app, dishes) -> None:
    client, _ = customer_client(app)
    order = place_order(client, dishes)
    assert cart_count(client) == 0
    response = client.post(f"/fa/account/orders/{order.public_token}/reorder")
    assert response.headers["Location"].endswith("/fa/cart")
    assert cart_count(client) == 3
    client.post(f"/fa/account/orders/{order.public_token}/reorder")  # adds up
    assert cart_count(client) == 6


def test_ordering_again_skips_what_is_no_longer_available(app, dishes) -> None:
    client, _ = customer_client(app)
    order = place_order(client, dishes)
    db.session.get(Dish, dishes[1].id).is_in_stock = False
    db.session.commit()
    response = client.post(
        f"/fa/account/orders/{order.public_token}/reorder", follow_redirects=True
    )
    assert cart_count(client) == 2
    assert "۱ مورد دیگر الان موجود نیست" in response.get_data(as_text=True)
    db.session.get(Dish, dishes[0].id).is_visible = False
    db.session.commit()
    again = client.post(f"/fa/account/orders/{order.public_token}/reorder")
    assert again.headers["Location"].endswith("/fa/account/orders")
    assert cart_count(client) == 0  # the first reorder's kebabs also left the cart


def test_ordering_again_rebuilds_a_custom_build_with_todays_prices(app) -> None:
    builder = add_builder()
    db.session.commit()
    ids = option_ids(builder, "baguette", "mayo")
    client, _ = customer_client(app)
    client.post("/api/cart/add-custom", json={"builder": "sandwich", "option_ids": ids})
    client.post("/fa/checkout", data=CHECKOUT)
    order = db.session.query(Order).one()
    assert order.items[0].builder_id == builder.id
    assert [o.option_id for o in order.items[0].options] == ids
    db.session.get(BuilderOption, ids[0]).price += 5_000
    db.session.commit()
    client.post(f"/fa/account/orders/{order.public_token}/reorder")
    assert cart_count(client) == 1
    lines = client.get("/api/cart").get_json()["lines"]
    assert lines[0]["unit_price"] == order.items[0].unit_price + 5_000


def test_a_build_with_a_deleted_option_is_skipped(app) -> None:
    builder = add_builder()
    db.session.commit()
    ids = option_ids(builder, "baguette", "mayo")
    client, _ = customer_client(app)
    client.post("/api/cart/add-custom", json={"builder": "sandwich", "option_ids": ids})
    client.post("/fa/checkout", data=CHECKOUT)
    order = db.session.query(Order).one()
    db.session.get(BuilderOption, ids[1]).is_in_stock = False
    db.session.commit()
    response = client.post(f"/fa/account/orders/{order.public_token}/reorder")
    assert response.headers["Location"].endswith("/fa/account/orders")
    assert cart_count(client) == 0


def test_another_customers_order_cannot_be_ordered_again(app, dishes) -> None:
    owner, _ = customer_client(app)
    order = place_order(owner, dishes)
    other, _ = customer_client(app, phone="09127654321", name="Other")
    assert other.post(f"/fa/account/orders/{order.public_token}/reorder").status_code == 404
    guest_order = place_order(app.test_client(), dishes)
    assert other.post(f"/fa/account/orders/{guest_order.public_token}/reorder").status_code == 404


# --- bookings --------------------------------------------------------------------------------


NOW = datetime(2026, 10, 26, 10, 0)  # a Monday, 10:00
TOMORROW = "2026-10-27"


@pytest.fixture
def fixed_clock(monkeypatch):
    """The booking page and the account pages read the clock from their own modules."""
    monkeypatch.setattr("restaurant.blueprints.public.reserve_routes.now_tehran", lambda: NOW)
    monkeypatch.setattr("restaurant.blueprints.public.account_routes.now_tehran", lambda: NOW)


def book(client, table_id, **form):
    return client.post(
        "/fa/reserve",
        data={
            "date": TOMORROW,
            "time": "19:00",
            "guests": "2",
            "table_id": str(table_id),
            "customer_name": "Sara",
            "customer_phone": "09121234567",
            "note": "",
            **form,
        },
    )


def test_a_booking_made_while_signed_in_shows_in_the_account(app, fixed_clock) -> None:
    table = add_tables(4)[0]
    db.session.commit()
    client, user = customer_client(app)
    reserve_page = client.get("/fa/reserve").get_data(as_text=True)
    assert 'value="Sara Customer"' in reserve_page and 'value="09121234567"' in reserve_page
    assert book(client, table.id).status_code == 302
    booking = db.session.query(Reservation).one()
    assert booking.user_id == user.id
    html = client.get("/fa/account/reservations").get_data(as_text=True)
    assert f"/fa/reservation/{booking.public_token}" in html
    assert "رزرو پیش‌رویی ندارید" not in html
    assert "رزروی ثبت نشده" not in html


def test_past_and_cancelled_bookings_are_listed_apart(app, fixed_clock) -> None:
    client, user = customer_client(app)
    for offset, status in ((-2, ReservationStatus.CONFIRMED), (2, ReservationStatus.CANCELLED)):
        start = (NOW + timedelta(days=offset)).replace(hour=19)
        db.session.add(
            Reservation(
                public_token=f"tok{offset}",
                user_id=user.id,
                table_label="1",
                language_code="fa",
                customer_name="Sara",
                customer_phone="09121234567",
                guests=2,
                starts_at=start,
                ends_at=start + timedelta(hours=1),
                status=status,
            )
        )
    db.session.commit()
    html = client.get("/fa/account/reservations").get_data(as_text=True)
    assert "رزروهای گذشته" in html and "tok-2" in html and "tok2" in html
    assert "رزرو پیش‌رویی ندارید" in html


def test_a_guest_booking_stays_a_guest_booking(app, fixed_clock) -> None:
    table = add_tables(4)[0]
    db.session.commit()
    assert book(app.test_client(), table.id).status_code == 302
    assert db.session.query(Reservation).one().user_id is None


# --- addresses -------------------------------------------------------------------------------

ADDRESS = {"label": "Home", "text": "Tehran, Azadi Street, number 12", "is_default": "y"}


def test_adding_editing_and_deleting_addresses(app) -> None:
    client, user = customer_client(app)
    assert client.post("/fa/account/addresses", data=ADDRESS).status_code == 302
    client.post(
        "/fa/account/addresses", data={"label": "Work", "text": "Tehran, Valiasr Street, no. 5"}
    )
    first, second = sorted(db.session.query(Address).all(), key=lambda a: a.id)
    assert (first.is_default, second.is_default) == (True, False)
    client.post(f"/fa/account/addresses/{second.id}/default")
    db.session.refresh(first)
    db.session.refresh(second)
    assert (first.is_default, second.is_default) == (False, True)
    edit = client.post(
        f"/fa/account/addresses/{first.id}/edit",
        data={"label": "Parents", "text": "Shiraz, Zand Street, number 9"},
    )
    assert edit.status_code == 302
    db.session.refresh(first)
    assert first.label == "Parents" and first.text == "Shiraz, Zand Street, number 9"
    client.post(f"/fa/account/addresses/{second.id}/delete")  # the default goes: another takes over
    db.session.refresh(first)
    assert db.session.query(Address).count() == 1 and first.is_default is True
    assert user.addresses[0].id == first.id


def test_the_first_address_is_always_the_default(app) -> None:
    client, _ = customer_client(app)
    client.post("/fa/account/addresses", data={"label": "", "text": "Tehran, Azadi Street, 12"})
    assert db.session.query(Address).one().is_default is True


def test_address_validation_and_the_limit(app) -> None:
    client, _ = customer_client(app)
    short = client.post("/fa/account/addresses", data={"label": "x", "text": "short"})
    assert short.status_code == 200 and "آدرس را کامل بنویسید" in short.get_data(as_text=True)
    for number in range(10):
        client.post(
            "/fa/account/addresses", data={"label": "", "text": f"Tehran, Street {number}, no. 1"}
        )
    over = client.post(
        "/en/account/addresses", data={"label": "", "text": "Tehran, one more, no. 1"}
    )
    assert "up to 10 addresses" in over.get_data(as_text=True)
    assert db.session.query(Address).count() == 10


def test_nobody_can_touch_another_customers_address(app) -> None:
    owner, user = customer_client(app)
    owner.post("/fa/account/addresses", data=ADDRESS)
    address = db.session.query(Address).one()
    other, _ = customer_client(app, phone="09127654321", name="Other")
    assert other.get(f"/fa/account/addresses/{address.id}/edit").status_code == 404
    assert other.post(f"/fa/account/addresses/{address.id}/edit", data=ADDRESS).status_code == 404
    assert other.post(f"/fa/account/addresses/{address.id}/delete").status_code == 404
    assert other.post(f"/fa/account/addresses/{address.id}/default").status_code == 404
    assert db.session.query(Address).count() == 1


def test_checkout_is_prefilled_and_can_remember_the_address(app, dishes) -> None:
    client, _ = customer_client(app)
    client.post("/fa/account/addresses", data=ADDRESS)
    add_to_cart(client, dishes[0])
    html = client.get("/fa/checkout").get_data(as_text=True)
    assert 'value="Sara Customer"' in html and 'value="09121234567"' in html
    assert "Tehran, Azadi Street, number 12" in html and "data-fill-address" in html
    new_address = "Tehran, Enghelab Square, number 3"
    form = {
        **CHECKOUT,
        "fulfillment": "delivery",
        "delivery_address": new_address,
        "save_address": "y",
    }
    client.post("/fa/checkout", data=form)
    assert db.session.query(Address).count() == 2
    add_to_cart(client, dishes[0])
    client.post("/fa/checkout", data=form)  # the same address is not saved twice
    assert db.session.query(Address).count() == 2


def test_the_address_is_not_saved_for_takeaway_or_without_the_tick(app, dishes) -> None:
    client, _ = customer_client(app)
    add_to_cart(client, dishes[0])
    client.post(
        "/fa/checkout",
        data={**CHECKOUT, "delivery_address": "Tehran, Azadi, no. 1", "save_address": "y"},
    )
    add_to_cart(client, dishes[0])
    client.post(
        "/fa/checkout",
        data={**CHECKOUT, "fulfillment": "delivery", "delivery_address": "Tehran, Azadi, no. 1"},
    )
    assert db.session.query(Address).count() == 0


def test_guests_see_a_sign_in_hint_at_checkout(client, dishes) -> None:
    add_to_cart(client, dishes[0])
    html = client.get("/fa/checkout").get_data(as_text=True)
    assert "/fa/login?next=/fa/checkout" in html and "data-fill-address" not in html


# --- profile ---------------------------------------------------------------------------------


def test_the_profile_can_be_changed(app) -> None:
    client, user = customer_client(app, email="sara@example.com")
    page = client.get("/fa/account/profile").get_data(as_text=True)
    assert 'value="sara@example.com"' in page and "09121234567" in page
    client.post("/fa/account/profile", data={"customer_name": "Sara Z", "email": "NEW@example.com"})
    db.session.refresh(user)
    assert (user.display_name, user.email) == ("Sara Z", "new@example.com")
    client.post("/fa/account/profile", data={"customer_name": "Sara Z", "email": ""})
    db.session.refresh(user)
    assert user.email is None


def test_profile_errors(app) -> None:
    make_customer(phone="09120000001", email="taken@example.com", name="Taken")
    client, user = customer_client(app)
    taken = client.post(
        "/fa/account/profile", data={"customer_name": "Sara", "email": "taken@example.com"}
    )
    assert "برای حساب دیگری است" in taken.get_data(as_text=True)
    bad = client.post("/en/account/profile", data={"customer_name": "S", "email": "nope"})
    html = bad.get_data(as_text=True)
    assert "Enter a name" in html and "not valid" in html
    db.session.refresh(user)
    assert user.display_name == "Sara Customer"


def test_the_password_can_be_changed(app) -> None:
    client, user = customer_client(app)
    wrong = client.post(
        "/fa/account/password",
        data={
            "current_password": "nope-nope",
            "new_password": "brand-new-pass",
            "new_password_again": "brand-new-pass",
        },
    )
    assert "رمز عبور فعلی درست نیست" in wrong.get_data(as_text=True)
    mismatch = client.post(
        "/fa/account/password",
        data={
            "current_password": CUSTOMER_PASSWORD,
            "new_password": "brand-new-pass",
            "new_password_again": "other-pass-1",
        },
    )
    assert "یکی نیستند" in mismatch.get_data(as_text=True)
    done = client.post(
        "/fa/account/password",
        data={
            "current_password": CUSTOMER_PASSWORD,
            "new_password": "brand-new-pass",
            "new_password_again": "brand-new-pass",
        },
    )
    assert done.status_code == 302
    fresh = app.test_client()
    assert customer_sign_in(fresh, user.phone, CUSTOMER_PASSWORD).status_code == 200
    assert customer_sign_in(fresh, user.phone, "brand-new-pass").status_code == 302


# --- the cart follows the account ------------------------------------------------------------


def test_a_guest_cart_survives_signing_in(app, dishes) -> None:
    make_customer()
    client = app.test_client()
    add_to_cart(client, dishes[0], 2)
    customer_sign_in(client, "09121234567")
    assert cart_count(client) == 2


def test_the_cart_follows_the_account_to_another_device_and_merges(app, dishes) -> None:
    make_customer()
    laptop = app.test_client()
    customer_sign_in(laptop, "09121234567")
    add_to_cart(laptop, dishes[0], 2)
    add_to_cart(laptop, dishes[1], 1)
    phone = app.test_client()
    add_to_cart(phone, dishes[0], 1)  # a guest cart on the other device
    customer_sign_in(phone, "09121234567")
    lines = {
        line["dish_id"]: line["quantity"] for line in phone.get("/api/cart").get_json()["lines"]
    }
    assert lines == {dishes[0].id: 3, dishes[1].id: 1}
    user = db.session.query(User).one()
    assert user.saved_cart and "dish_id" in user.saved_cart


def test_placing_an_order_empties_the_saved_cart_too(app, dishes) -> None:
    client, user = customer_client(app)
    place_order(client, dishes)
    db.session.refresh(user)
    assert user.saved_cart == "[]"
    other = app.test_client()
    customer_sign_in(other, user.phone)
    assert cart_count(other) == 0


def test_a_damaged_saved_cart_is_ignored(app, dishes) -> None:
    user = make_customer()
    user.saved_cart = "{not json"
    db.session.commit()
    client = app.test_client()
    add_to_cart(client, dishes[0])
    assert customer_sign_in(client, user.phone).status_code == 302
    assert cart_count(client) == 1
