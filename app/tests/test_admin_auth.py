"""Sign-in, sign-out, permissions on routes, the panel language and the rate limit."""

import pytest

from restaurant import create_app
from restaurant.extensions import db
from tests.conftest import add_two_languages
from tests.helpers import STAFF_PASSWORD, make_staff, sign_in, staff_client


def test_panel_pages_redirect_visitors_to_sign_in(client) -> None:
    response = client.get("/admin/dashboard")
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/admin/login?next=")


def test_sign_in_page_renders_in_both_languages(client) -> None:
    fa = client.get("/admin/login")
    assert 'dir="rtl"' in fa.get_data(as_text=True)
    assert "ورود به پنل مدیریت" in fa.get_data(as_text=True)
    client.get("/admin/language/en")
    en = client.get("/admin/login").get_data(as_text=True)
    assert 'dir="ltr"' in en and "Sign in to the admin panel" in en


def test_correct_credentials_sign_in(app, client) -> None:
    make_staff("admin")
    response = sign_in(client, "admin@example.com")
    assert response.status_code == 302
    assert response.headers["Location"] == "/admin/dashboard"


@pytest.mark.parametrize(
    ("email", "password", "message"),
    [
        ("cashier@example.com", "wrong-password", "ایمیل یا گذرواژه درست نیست"),
        ("nobody@example.com", STAFF_PASSWORD, "ایمیل یا گذرواژه درست نیست"),
        ("blocked@example.com", STAFF_PASSWORD, "مسدود شده"),
    ],
)
def test_failed_sign_in_shows_a_message(app, client, email, password, message) -> None:
    make_staff("cashier")
    make_staff("cashier", "blocked@example.com", is_active=False)
    response = sign_in(client, email, password)
    assert response.status_code == 200
    assert message in response.get_data(as_text=True)


def test_empty_form_is_refused(app, client) -> None:
    response = client.post("/admin/login", data={})
    assert "ایمیل و گذرواژه را وارد کنید" in response.get_data(as_text=True)


def test_next_address_is_followed_only_inside_the_panel(app, client) -> None:
    make_staff("admin")
    ok = client.post(
        "/admin/login?next=/admin/dashboard",
        data={"email": "admin@example.com", "password": STAFF_PASSWORD},
    )
    assert ok.headers["Location"] == "/admin/dashboard"
    client.post("/admin/logout")
    for evil in ("https://evil.example/", "//evil.example/", "/fa/menu", "javascript:alert(1)"):
        response = client.post(
            "/admin/login",
            query_string={"next": evil},
            data={"email": "admin@example.com", "password": STAFF_PASSWORD},
        )
        assert response.headers["Location"] == "/admin/dashboard"
        client.post("/admin/logout")


def test_sign_out_ends_the_session(app) -> None:
    client = staff_client(app, "admin")
    assert client.get("/admin/dashboard").status_code == 200
    client.post("/admin/logout")
    assert client.get("/admin/dashboard").status_code == 302


def test_a_user_blocked_while_signed_in_is_signed_out(app) -> None:
    user = make_staff("admin")
    client = app.test_client()
    sign_in(client, user.email)
    assert client.get("/admin/dashboard").status_code == 200
    user.is_active = False
    db.session.commit()
    assert client.get("/admin/dashboard").status_code == 302


def test_role_without_the_dashboard_gets_403(app) -> None:
    client = staff_client(app, "kitchen")
    response = client.get("/admin/dashboard")
    assert response.status_code == 403
    assert "دسترسی ندارید" in response.get_data(as_text=True)


def test_dashboard_hides_money_from_roles_without_it(app) -> None:
    manager = staff_client(app, "manager")  # has money
    text = manager.get("/admin/dashboard").get_data(as_text=True)
    assert "فروش امروز" in text
    viewer_no_money = make_staff("viewer", "v@example.com")
    # Remove money from the viewer role to model a dashboard-only role.
    from restaurant.models import Role

    role = db.session.query(Role).filter_by(key="viewer").one()
    role.grants = [g for g in role.grants if g.permission.key != "money"]
    db.session.commit()
    client = app.test_client()
    sign_in(client, viewer_no_money.email)
    text = client.get("/admin/dashboard").get_data(as_text=True)
    assert "فروش امروز" not in text and "سفارش‌های امروز" in text


def test_view_only_role_sees_the_notice(app) -> None:
    client = staff_client(app, "viewer")
    assert "فقط حق مشاهده" in client.get("/admin/dashboard").get_data(as_text=True)


def test_panel_language_switch_is_remembered(app) -> None:
    client = staff_client(app, "admin")
    client.get("/admin/language/en?next=/admin/dashboard")
    page = client.get("/admin/dashboard").get_data(as_text=True)
    assert 'lang="en"' in page and "Orders today" in page
    # An unknown code changes nothing.
    client.get("/admin/language/de")
    assert "Orders today" in client.get("/admin/dashboard").get_data(as_text=True)


def test_sign_in_is_rate_limited() -> None:
    app = create_app("test", {"RATELIMIT_ENABLED": True, "LOGIN_RATE_LIMIT": "3 per minute"})
    with app.app_context():
        db.create_all()
        add_two_languages()
        client = app.test_client()
        statuses = [
            client.post("/admin/login", data={"email": "a@b.co", "password": "x"}).status_code
            for _ in range(5)
        ]
        db.session.remove()
        db.drop_all()
    assert statuses[:3] == [200, 200, 200]
    assert statuses[3:] == [429, 429]


def test_post_without_csrf_token_is_refused_when_protection_is_on() -> None:
    app = create_app("test", {"WTF_CSRF_ENABLED": True})
    with app.app_context():
        db.create_all()
        add_two_languages()
        response = app.test_client().post("/admin/login", data={"email": "a", "password": "b"})
        db.session.remove()
        db.drop_all()
    assert response.status_code == 400


def test_create_admin_command_makes_an_account_that_can_sign_in(app) -> None:
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=["create-admin", "--email", "Boss@Example.com", "--name", "Boss"],
        input="long-enough-1\nlong-enough-1\n",
    )
    assert result.exit_code == 0, result.output
    assert sign_in(app.test_client(), "boss@example.com", "long-enough-1").status_code == 302
    again = runner.invoke(
        args=["create-admin", "--email", "boss@example.com", "--name", "Boss"],
        input="long-enough-1\nlong-enough-1\n",
    )
    assert again.exit_code != 0 and "Could not create" in again.output


def test_create_admin_refuses_a_short_password(app) -> None:
    result = app.test_cli_runner().invoke(
        args=["create-admin", "--email", "b@example.com", "--name", "B"], input="short\nshort\n"
    )
    assert result.exit_code != 0


def test_seed_demo_adds_staff_once(app) -> None:
    runner = app.test_cli_runner()
    first = runner.invoke(args=["seed-demo"]).output
    second = runner.invoke(args=["seed-demo"]).output
    assert "added 5 sample staff accounts" in first
    assert "sample staff" not in second
    assert sign_in(app.test_client(), "kitchen@example.com", "demo-pass-1234").status_code == 302
