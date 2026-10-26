"""The contact form and the admin "Customers and messages" section."""

import pytest

from restaurant.constants import FulfillmentType, PaymentMethod
from restaurant.extensions import db
from restaurant.models import ContactMessage, Order, User
from tests.helpers import (
    customer_client,
    make_customer,
    staff_client,
)

MESSAGE = {
    "customer_name": "Sara",
    "contact": "09121234567",
    "body": "Do you have gluten free pizza?",
}


def add_order(user: User, total: int = 100_000) -> Order:
    order = Order(
        public_token=f"tok{user.id}-{total}",
        user_id=user.id,
        language_code="fa",
        customer_name=user.display_name,
        customer_phone=user.phone,
        fulfillment=FulfillmentType.TAKEAWAY,
        payment_method=PaymentMethod.CASH_ON_SITE,
        subtotal=total,
        total=total,
    )
    db.session.add(order)
    db.session.commit()
    return order


# --- the contact form ------------------------------------------------------------------------


def test_the_contact_page_opens_in_both_languages(client) -> None:
    assert "تماس با ما" in client.get("/fa/contact").get_data(as_text=True)
    assert "Contact us" in client.get("/en/contact").get_data(as_text=True)


def test_a_message_is_stored_with_its_language(client) -> None:
    response = client.post("/en/contact", data=MESSAGE)
    assert response.status_code == 302
    message = db.session.query(ContactMessage).one()
    assert (message.name, message.contact, message.language_code) == ("Sara", "09121234567", "en")
    assert message.user_id is None and message.is_read is False
    assert "Your message was sent" in client.get("/en/contact").get_data(as_text=True)


def test_an_email_can_be_the_way_to_answer(client) -> None:
    client.post("/fa/contact", data={**MESSAGE, "contact": "Sara@Example.com"})
    assert db.session.query(ContactMessage).one().contact == "sara@example.com"


@pytest.mark.parametrize(
    ("overrides", "text"),
    [
        ({"customer_name": "S"}, "نام را بنویسید"),
        ({"contact": "hello"}, "شماره موبایل یا ایمیل معتبر"),
        ({"body": "hi"}, "پیام را بنویسید"),
        ({"body": "x" * 2001}, "پیام را بنویسید"),
    ],
)
def test_bad_messages_are_refused(client, overrides, text) -> None:
    response = client.post("/fa/contact", data={**MESSAGE, **overrides})
    assert response.status_code == 200 and text in response.get_data(as_text=True)
    assert db.session.query(ContactMessage).count() == 0


def test_a_signed_in_customer_gets_the_form_filled_and_the_message_linked(app) -> None:
    client, user = customer_client(app)
    html = client.get("/fa/contact").get_data(as_text=True)
    assert 'value="Sara Customer"' in html and 'value="09121234567"' in html
    client.post("/fa/contact", data=MESSAGE)
    assert db.session.query(ContactMessage).one().user_id == user.id


# --- customers in the panel ------------------------------------------------------------------


def test_each_role_sees_the_customers_section_as_the_defaults_say(app) -> None:
    for role, expected in (("manager", 200), ("cashier", 200), ("viewer", 200), ("kitchen", 403)):
        client = staff_client(app, role)
        assert client.get("/admin/customers").status_code == expected, role
        assert client.get("/admin/messages").status_code == expected, role


def test_the_sidebar_links_the_section(app) -> None:
    html = staff_client(app, "manager").get("/admin/customers").get_data(as_text=True)
    assert "/admin/customers" in html and "مشتریان و پیام‌ها" in html


def test_the_customer_list_shows_customers_with_their_numbers(app) -> None:
    sara = make_customer(name="Sara Customer")
    make_customer(phone="09127654321", name="Reza Other", email="reza@example.com")
    add_order(sara, 120_000)
    add_order(sara, 80_000)
    manager = staff_client(app, "manager")
    html = manager.get("/admin/customers").get_data(as_text=True)
    assert "Sara Customer" in html and "Reza Other" in html and "reza@example.com" in html
    assert "۲۰۰٬۰۰۰" in html  # what Sara spent


def test_customers_are_found_by_name_phone_or_email_and_staff_are_not_listed(app) -> None:
    make_customer(name="Sara Customer")
    make_customer(phone="09127654321", name="Reza Other", email="reza@example.com")
    manager = staff_client(app, "manager")
    for query, found, absent in (
        ("Sara", "Sara Customer", "Reza Other"),
        ("09127", "Reza Other", "Sara Customer"),
        ("reza@", "Reza Other", "Sara Customer"),
    ):
        html = manager.get(f"/admin/customers?q={query}").get_data(as_text=True)
        assert found in html and absent not in html
    nothing = manager.get("/admin/customers?q=zzz").get_data(as_text=True)
    assert "مشتری‌ای با این جست‌وجو پیدا نشد" in nothing
    assert (
        "Manager" not in manager.get("/admin/customers").get_data(as_text=True).split("<table")[-1]
    )


def test_the_money_permission_hides_what_a_customer_spent(app) -> None:
    from restaurant.constants import AccessLevel
    from restaurant.models import Role

    sara = make_customer()
    add_order(sara, 120_000)
    manager = staff_client(app, "manager")
    assert "۱۲۰٬۰۰۰" in manager.get("/admin/customers").get_data(as_text=True)
    role = db.session.query(Role).filter_by(key="manager").one()
    for grant in role.grants:
        if grant.permission.key == "money":
            grant.access_level = AccessLevel.NONE
    db.session.commit()
    assert "۱۲۰٬۰۰۰" not in manager.get("/admin/customers").get_data(as_text=True)
    assert "۱۲۰٬۰۰۰" not in manager.get(f"/admin/customers/{sara.id}").get_data(as_text=True)


def test_the_customer_page_shows_orders_bookings_and_addresses(app) -> None:
    from restaurant.models import Address

    sara = make_customer()
    add_order(sara, 120_000)
    db.session.add(Address(user_id=sara.id, label="Home", text="Tehran, Azadi St 12"))
    db.session.commit()
    html = staff_client(app, "manager").get(f"/admin/customers/{sara.id}").get_data(as_text=True)
    assert "Sara Customer" in html and "Tehran, Azadi St 12" in html and "۱۲۰٬۰۰۰" in html
    assert "رزروی ندارد" in html


def test_staff_and_unknown_ids_have_no_customer_page(app) -> None:
    manager = staff_client(app, "manager")
    staff_id = db.session.query(User).filter(User.roles.any()).first().id
    assert manager.get(f"/admin/customers/{staff_id}").status_code == 404
    assert manager.get("/admin/customers/9999").status_code == 404


def test_blocking_and_unblocking_a_customer(app) -> None:
    sara = make_customer()
    manager = staff_client(app, "manager")
    response = manager.post(f"/admin/customers/{sara.id}/active", data={"active": "0"})
    assert response.status_code == 302
    db.session.refresh(sara)
    assert sara.is_active is False
    blocked = app.test_client().post(
        "/fa/login", data={"identifier": sara.phone, "password": "customer-pass-1"}
    )
    assert "مسدود" in blocked.get_data(as_text=True)
    manager.post(f"/admin/customers/{sara.id}/active", data={"active": "1"})
    db.session.refresh(sara)
    assert sara.is_active is True


def test_a_blocked_customer_who_is_signed_in_is_signed_out(app) -> None:
    client, user = customer_client(app)
    assert client.get("/fa/account").status_code == 200
    user.is_active = False
    db.session.commit()
    assert client.get("/fa/account").status_code == 302


def test_view_only_staff_cannot_block(app) -> None:
    sara = make_customer()
    for role in ("viewer", "cashier"):
        client = staff_client(app, role)
        assert (
            client.post(f"/admin/customers/{sara.id}/active", data={"active": "0"}).status_code
            == 403
        )
    db.session.refresh(sara)
    assert sara.is_active is True


# --- messages in the panel -------------------------------------------------------------------


def add_message(**fields) -> ContactMessage:
    message = ContactMessage(
        name=fields.pop("name", "Sara"),
        contact=fields.pop("contact", "09121234567"),
        body=fields.pop("body", "Hello there, restaurant"),
        language_code="fa",
        **fields,
    )
    db.session.add(message)
    db.session.commit()
    return message


def test_the_inbox_lists_messages_newest_first_and_counts_unread(app) -> None:
    add_message(name="First", body="first message text")
    add_message(name="Second", body="second message text", is_read=True)
    html = staff_client(app, "manager").get("/admin/messages").get_data(as_text=True)
    assert html.index("Second") < html.index("First")
    assert "۱ پیام خوانده‌نشده" in html


def test_the_unread_count_shows_on_the_customers_tab(app) -> None:
    add_message()
    html = staff_client(app, "manager").get("/admin/customers").get_data(as_text=True)
    assert 'badge badge--pending">۱<' in html


def test_marking_a_message_read_unread_and_deleting_it(app) -> None:
    message = add_message()
    manager = staff_client(app, "manager")
    manager.post(f"/admin/messages/{message.id}/read", data={"read": "1"})
    db.session.refresh(message)
    assert message.is_read is True
    manager.post(f"/admin/messages/{message.id}/read", data={"read": "0"})
    db.session.refresh(message)
    assert message.is_read is False
    assert manager.post(f"/admin/messages/{message.id}/delete").status_code == 302
    assert db.session.query(ContactMessage).count() == 0
    assert manager.post(f"/admin/messages/{message.id}/delete").status_code == 404
    assert manager.post("/admin/messages/999/read", data={"read": "1"}).status_code == 404


def test_view_only_staff_can_read_but_not_change_messages(app) -> None:
    message = add_message()
    viewer = staff_client(app, "viewer")
    assert "Hello there" in viewer.get("/admin/messages").get_data(as_text=True)
    assert viewer.post(f"/admin/messages/{message.id}/read", data={"read": "1"}).status_code == 403
    assert viewer.post(f"/admin/messages/{message.id}/delete").status_code == 403
    assert db.session.query(ContactMessage).count() == 1


def test_the_demo_seed_adds_a_customer_and_messages_once(app) -> None:
    from restaurant.service_factory import make_demo_customer_seeder

    assert make_demo_customer_seeder().seed() == 4
    db.session.commit()
    assert make_demo_customer_seeder().seed() == 0
    customer = db.session.query(User).filter_by(email="customer@example.com").one()
    assert customer.addresses and customer.registration_pending is False
    client = app.test_client()
    response = client.post(
        "/fa/login", data={"identifier": "09120000000", "password": "demo-pass-1234"}
    )
    assert response.status_code == 302
