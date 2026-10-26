"""Customer registration with a phone code, sign-in, sign-out and the guest history."""

from datetime import timedelta

import pytest

from restaurant.constants import FulfillmentType, PaymentMethod
from restaurant.extensions import db
from restaurant.models import Order, User, VerificationCode
from restaurant.service_factory import make_customer_auth_service
from restaurant.services import (
    CodeOutcome,
    CustomerLoginOutcome,
    RegistrationError,
    RegistrationProblem,
    RegistrationRequest,
)
from restaurant.timeutils import now_tehran
from tests.helpers import (
    CUSTOMER_PASSWORD,
    DEMO_CODE,
    add_category,
    add_dish,
    customer_sign_in,
    make_customer,
    make_staff,
    register,
)


def request_for(**overrides) -> RegistrationRequest:
    values = {
        "name": "Sara",
        "phone": "09121234567",
        "email": "",
        "password": CUSTOMER_PASSWORD,
        **overrides,
    }
    return RegistrationRequest(**values)


def only_user() -> User:
    return db.session.query(User).one()


# --- the service -------------------------------------------------------------------------


def test_registering_creates_a_pending_account_and_a_hashed_code(app) -> None:
    user = make_customer_auth_service().register(request_for(phone="۰۹۱۲ ۱۲۳ ۴۵۶۷"))
    db.session.commit()
    assert user.phone == "09121234567" and user.registration_pending is True
    stored = db.session.query(VerificationCode).one()
    assert stored.user_id == user.id and DEMO_CODE not in stored.code_hash
    assert user.password_hash and CUSTOMER_PASSWORD not in user.password_hash


@pytest.mark.parametrize(
    ("overrides", "problem"),
    [
        ({"name": "S"}, RegistrationProblem.BAD_NAME),
        ({"phone": "12345"}, RegistrationProblem.BAD_PHONE),
        ({"email": "not-an-email"}, RegistrationProblem.BAD_EMAIL),
        ({"password": "short"}, RegistrationProblem.WEAK_PASSWORD),
    ],
)
def test_bad_registrations_are_refused(app, overrides, problem) -> None:
    with pytest.raises(RegistrationError) as caught:
        make_customer_auth_service().register(request_for(**overrides))
    assert caught.value.problem is problem
    assert db.session.query(User).count() == 0


def test_a_phone_or_email_already_in_use_is_refused(app) -> None:
    make_customer(phone="09121234567", email="a@example.com")
    for overrides, problem in (
        ({}, RegistrationProblem.PHONE_TAKEN),
        ({"phone": "09127654321", "email": "A@example.com"}, RegistrationProblem.EMAIL_TAKEN),
    ):
        with pytest.raises(RegistrationError) as caught:
            make_customer_auth_service().register(request_for(**overrides))
        assert caught.value.problem is problem


def test_an_unverified_registration_can_be_started_again_with_the_same_phone(app) -> None:
    service = make_customer_auth_service()
    first = service.register(request_for(name="First"))
    second = service.register(request_for(name="Second", email="new@example.com"))
    db.session.commit()
    assert first.id == second.id and db.session.query(User).count() == 1
    assert only_user().display_name == "Second"
    assert db.session.query(VerificationCode).count() == 1


def test_the_right_code_activates_the_account(app) -> None:
    service = make_customer_auth_service()
    user = service.register(request_for())
    outcome, verified = service.verify(user.id, f" {DEMO_CODE} ")
    db.session.commit()
    assert outcome is CodeOutcome.OK and verified is user
    assert user.registration_pending is False
    assert db.session.query(VerificationCode).count() == 0


def test_a_wrong_code_counts_and_the_fifth_wrong_try_locks_the_code(app) -> None:
    service = make_customer_auth_service()
    user = service.register(request_for())
    for _ in range(5):
        assert service.verify(user.id, "00000")[0] is CodeOutcome.WRONG
    assert service.verify(user.id, DEMO_CODE)[0] is CodeOutcome.TOO_MANY
    assert user.registration_pending is True
    service.send_code(user)  # a fresh code starts again
    assert service.verify(user.id, DEMO_CODE)[0] is CodeOutcome.OK


def test_an_old_code_expires(app) -> None:
    service = make_customer_auth_service()
    user = service.register(request_for())
    db.session.query(VerificationCode).one().expires_at = now_tehran() - timedelta(seconds=1)
    assert service.verify(user.id, DEMO_CODE)[0] is CodeOutcome.EXPIRED


def test_nothing_to_verify_for_an_active_or_unknown_account(app) -> None:
    customer = make_customer()
    service = make_customer_auth_service()
    assert service.verify(customer.id, DEMO_CODE)[0] is CodeOutcome.NOTHING_PENDING
    assert service.verify(9999, DEMO_CODE)[0] is CodeOutcome.NOTHING_PENDING


def test_sign_in_by_phone_or_email_and_the_failures(app) -> None:
    make_customer(phone="09121234567", email="sara@example.com")
    service = make_customer_auth_service()
    for identifier in ("09121234567", "۰۹۱۲۱۲۳۴۵۶۷", "+989121234567", "SARA@example.com"):
        assert service.authenticate(identifier, CUSTOMER_PASSWORD).outcome is (
            CustomerLoginOutcome.OK
        )
    for identifier, password in (("09121234567", "wrong-pass"), ("09129999999", CUSTOMER_PASSWORD)):
        assert service.authenticate(identifier, password).outcome is CustomerLoginOutcome.INVALID
    assert service.authenticate("", "x").outcome is CustomerLoginOutcome.INVALID


def test_a_blocked_customer_cannot_sign_in(app) -> None:
    make_customer(is_active=False)
    result = make_customer_auth_service().authenticate("09121234567", CUSTOMER_PASSWORD)
    assert result.outcome is CustomerLoginOutcome.BLOCKED


def test_signing_in_to_an_unverified_account_asks_for_a_new_code(app) -> None:
    service = make_customer_auth_service()
    service.register(request_for())
    result = service.authenticate("09121234567", CUSTOMER_PASSWORD)
    assert result.outcome is CustomerLoginOutcome.NEEDS_CODE
    assert db.session.query(VerificationCode).count() == 1


def test_verifying_joins_the_guest_orders_and_bookings_of_that_phone(app) -> None:
    category = add_category("a", {"fa": "الف", "en": "A"})
    add_dish(category, {"fa": "کباب", "en": "Kebab"}, base_price=100_000)
    db.session.commit()
    guest_order = Order(
        public_token="t1",
        language_code="fa",
        customer_name="Sara",
        customer_phone="09121234567",
        fulfillment=FulfillmentType.TAKEAWAY,
        payment_method=PaymentMethod.CASH_ON_SITE,
    )
    other_order = Order(
        public_token="t2",
        language_code="fa",
        customer_name="Other",
        customer_phone="09129999999",
        fulfillment=FulfillmentType.TAKEAWAY,
        payment_method=PaymentMethod.CASH_ON_SITE,
    )
    db.session.add_all([guest_order, other_order])
    db.session.commit()
    service = make_customer_auth_service()
    user = service.register(request_for())
    service.verify(user.id, DEMO_CODE)
    db.session.commit()
    assert guest_order.user_id == user.id and other_order.user_id is None


# --- the pages -----------------------------------------------------------------------------


def test_the_whole_registration_flow_in_the_browser(client) -> None:
    response = register(client)
    assert response.status_code == 302 and response.headers["Location"].endswith("/fa/verify")
    page = client.get("/fa/verify").get_data(as_text=True)
    assert "۰۹۱۲۱۲۳۴۵۶۷" in page
    wrong = client.post("/fa/verify", data={"code": "00000"})
    assert wrong.status_code == 200 and "کد درست نیست" in wrong.get_data(as_text=True)
    done = client.post("/fa/verify", data={"code": "۱۲۳۴۵"})
    assert done.status_code == 302 and done.headers["Location"].endswith("/fa/account")
    assert only_user().registration_pending is False
    assert "Sara Customer" in client.get("/fa/account").get_data(as_text=True)


def test_registration_errors_are_shown_in_the_page_language(client) -> None:
    english = register(client, lang="en", phone="123", password="x", password_again="y")
    html = english.get_data(as_text=True)
    assert english.status_code == 200
    assert "not a valid mobile number" in html
    assert "at least 8 characters" in html and "do not match" in html
    persian = register(client, phone="123")
    assert "شماره موبایل معتبر نیست" in persian.get_data(as_text=True)
    assert db.session.query(User).count() == 0


def test_a_taken_phone_is_reported_on_the_page(client) -> None:
    make_customer()
    html = register(client).get_data(as_text=True)
    assert "قبلاً حساب ساخته شده" in html


def test_the_verify_page_needs_a_pending_registration(client) -> None:
    assert client.get("/fa/verify").headers["Location"].endswith("/fa/login")
    assert client.post("/fa/verify", data={"code": DEMO_CODE}).status_code == 302


def test_resending_a_code_replaces_the_old_one(client) -> None:
    register(client)
    db.session.query(VerificationCode).one().attempts = 4
    db.session.commit()
    response = client.post("/fa/verify/resend")
    assert response.headers["Location"].endswith("/fa/verify")
    assert db.session.query(VerificationCode).one().attempts == 0


def test_demo_mode_shows_the_fixed_code_on_the_verify_page(app) -> None:
    app.config["DEMO_MODE"] = True
    client = app.test_client()
    register(client)
    assert "۱۲۳۴۵" in client.get("/fa/verify").get_data(as_text=True)
    app.config["DEMO_MODE"] = False
    assert "نسخهٔ نمایشی: پیامکی" not in client.get("/fa/verify").get_data(as_text=True)


def test_sign_in_page_and_sign_in(client) -> None:
    make_customer()
    assert client.get("/fa/login").status_code == 200
    bad = customer_sign_in(client, "09121234567", "wrong-pass")
    assert bad.status_code == 200 and "درست نیست" in bad.get_data(as_text=True)
    good = customer_sign_in(client, "09121234567")
    assert good.status_code == 302 and good.headers["Location"].endswith("/fa/account")
    assert client.get("/fa/login").status_code == 302  # already signed in


def test_signing_in_returns_to_the_page_asked_for_and_never_to_another_site(client) -> None:
    make_customer()
    guarded = client.get("/fa/account/orders")
    assert guarded.headers["Location"] == "/fa/login?next=/fa/account/orders"
    for target, expected in (
        ("/fa/checkout", "/fa/checkout"),
        ("https://evil.example/x", "/fa/account"),
        ("//evil.example/x", "/fa/account"),
    ):
        fresh = client.application.test_client()
        response = fresh.post(
            "/fa/login",
            data={"identifier": "09121234567", "password": CUSTOMER_PASSWORD, "next": target},
        )
        assert response.headers["Location"].endswith(expected)


def test_a_customer_cannot_open_the_admin_panel(client) -> None:
    make_customer(email="sara@example.com")
    response = client.post(
        "/admin/login", data={"email": "sara@example.com", "password": CUSTOMER_PASSWORD}
    )
    assert response.status_code == 200
    client.post("/fa/login", data={"identifier": "09121234567", "password": CUSTOMER_PASSWORD})
    assert client.get("/admin/orders").status_code == 403


def test_staff_can_sign_in_on_the_public_site_with_their_email(client) -> None:
    staff = make_staff("manager")
    response = client.post(
        "/fa/login", data={"identifier": staff.email, "password": "staff-password-1"}
    )
    assert response.status_code == 302


def test_signing_out_empties_the_cart_of_this_browser(client) -> None:
    category = add_category("a", {"fa": "الف", "en": "A"})
    dish = add_dish(category, {"fa": "کباب", "en": "Kebab"}, base_price=100_000)
    db.session.commit()
    make_customer()
    customer_sign_in(client, "09121234567")
    client.post("/api/cart/add", json={"dish_id": dish.id, "quantity": 1})
    assert client.get("/api/cart").get_json()["count"] == 1
    response = client.post("/fa/logout")
    assert response.status_code == 302
    assert client.get("/api/cart").get_json()["count"] == 0
    assert client.get("/fa/account").status_code == 302
    # the cart is kept with the account
    customer_sign_in(client, "09121234567")
    assert client.get("/api/cart").get_json()["count"] == 1


def test_staff_accounts_are_not_listed_as_customers_and_customers_are_not_staff(app) -> None:
    from restaurant.repositories import UserRepository

    make_staff("manager")
    make_customer()
    repository = UserRepository(db.session)
    assert [u.phone for u in repository.list_customers("", 0, 10)[0]] == ["09121234567"]
    assert all(user.roles for user in repository.list_staff())
