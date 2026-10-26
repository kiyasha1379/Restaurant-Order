"""The languages section: progress, switching English off, the default and the text editor."""

import pytest

from restaurant.extensions import db
from restaurant.models import Language, UiString, UiStringTranslation
from restaurant.service_factory import make_translation_service
from tests.helpers import add_category, add_dish, staff_client


def language(code: str) -> Language:
    return db.session.query(Language).filter_by(code=code).one()


@pytest.fixture
def two_dishes(app):
    category = add_category("pizza", {"fa": "پیتزا", "en": "Pizza"})
    add_dish(category, {"fa": "مارگاریتا", "en": "Margherita"}, base_price=1)
    add_dish(category, {"fa": "پپرونی"}, base_price=2)
    db.session.commit()


def test_overview_shows_translation_progress(app, two_dishes) -> None:
    make_translation_service().sync_defaults()
    db.session.commit()
    page = staff_client(app, "manager").get("/admin/languages").get_data(as_text=True)
    assert "فارسی" in page and "English" in page
    assert page.count('role="progressbar"') == 6
    assert 'aria-valuenow="50"' in page  # English dishes: 1 of 2
    assert 'aria-valuenow="100"' in page


def test_switching_english_off_hides_it_from_visitors_but_not_from_staff(app) -> None:
    client = staff_client(app, "manager")
    visitor = app.test_client()
    assert visitor.get("/en/menu").status_code == 200
    client.post(
        "/admin/languages/settings", data={"default_code": "fa"}
    )  # english_enabled missing = off
    assert not language("en").is_enabled and language("fa").is_enabled
    assert visitor.get("/en/menu").status_code == 302
    client.get("/admin/language/en")
    assert "Languages" in client.get("/admin/languages").get_data(as_text=True)
    client.post("/admin/languages/settings", data={"english_enabled": "1", "default_code": "fa"})
    assert visitor.get("/en/menu").status_code == 200


def test_default_language_can_change_but_not_to_a_disabled_one(app) -> None:
    client = staff_client(app, "manager")
    visitor = app.test_client()
    client.post("/admin/languages/settings", data={"english_enabled": "1", "default_code": "en"})
    assert visitor.get("/").headers["Location"].startswith("/en/")
    client.get("/admin/language/fa")
    response = client.post(
        "/admin/languages/settings", data={"default_code": "en"}, follow_redirects=True
    )
    assert "زبان پیش‌فرض نمی‌تواند خاموش باشد" in response.get_data(as_text=True)
    assert language("en").is_enabled and language("en").is_default
    assert client.post("/admin/languages/settings", data={"default_code": "de"}).status_code == 302
    assert language("en").is_default


def test_text_editor_lists_filters_and_saves(app) -> None:
    make_translation_service().sync_defaults()
    db.session.commit()
    client = staff_client(app, "manager")
    page = client.get("/admin/languages/texts?q=home.cta_order").get_data(as_text=True)
    assert "home.cta_order" in page and "Order online" in page and "سفارش آنلاین" in page
    response = client.post(
        "/admin/languages/texts",
        data={
            "keys": ["home.cta_order"],
            "text:fa:home.cta_order": "همین حالا سفارش بده",
            "text:en:home.cta_order": "Order right now",
            "next": "/admin/languages/texts?q=home.cta_order",
        },
    )
    assert response.headers["Location"] == "/admin/languages/texts?q=home.cta_order"
    visitor = app.test_client()
    assert "همین حالا سفارش بده" in visitor.get("/fa/").get_data(as_text=True)
    assert "Order right now" in visitor.get("/en/").get_data(as_text=True)


def test_only_changed_texts_are_stored_and_empty_resets_to_the_default(app) -> None:
    client = staff_client(app, "manager")
    key = "home.cta_order"
    assert db.session.query(UiString).count() == 0
    client.post(
        "/admin/languages/texts",
        data={"keys": [key], f"text:fa:{key}": "سفارش آنلاین", f"text:en:{key}": "Order online"},
    )
    assert db.session.query(UiStringTranslation).count() == 0  # unchanged: nothing stored
    client.post("/admin/languages/texts", data={"keys": [key], f"text:en:{key}": "Order now"})
    assert "Order now" in app.test_client().get("/en/").get_data(as_text=True)
    client.post("/admin/languages/texts", data={"keys": [key], f"text:en:{key}": "   "})
    assert "Order online" in app.test_client().get("/en/").get_data(as_text=True)


def test_unknown_keys_and_unsafe_redirects_are_ignored(app) -> None:
    client = staff_client(app, "manager")
    response = client.post(
        "/admin/languages/texts",
        data={"keys": ["evil.key"], "text:en:evil.key": "x", "next": "https://evil.example/"},
    )
    assert response.headers["Location"] == "/admin/languages/texts"
    assert db.session.query(UiString).count() == 0


def test_missing_filter_lists_texts_without_a_translation(app) -> None:
    db.session.add(UiString(key="custom.only_persian"))
    db.session.flush()
    from restaurant.repositories import UiStringRepository

    UiStringRepository(db.session).save_text("custom.only_persian", language("fa"), "فقط فارسی")
    db.session.commit()
    client = staff_client(app, "manager")
    page = client.get("/admin/languages/texts?missing=en").get_data(as_text=True)
    assert "custom.only_persian" in page and "home.cta_order" not in page
    assert "۱ متن" in client.get("/admin/languages").get_data(as_text=True)
    assert "۱ سفارش" in page  # the result counter


def test_text_editor_paginates(app) -> None:
    client = staff_client(app, "manager")
    first = client.get("/admin/languages/texts").get_data(as_text=True)
    assert first.count('name="keys"') == 25
    assert "?page=2" in first or "page=2" in first
    assert client.get("/admin/languages/texts?page=999").status_code == 200


def test_view_only_role_cannot_change_languages_or_texts(app) -> None:
    client = staff_client(app, "viewer")
    page = client.get("/admin/languages").get_data(as_text=True)
    assert "disabled" in page and "فقط حق مشاهده" in page
    assert client.post("/admin/languages/settings", data={}).status_code == 403
    assert (
        client.post("/admin/languages/texts", data={"keys": ["home.cta_order"]}).status_code == 403
    )
    assert language("en").is_enabled
    assert client.get("/admin/languages/texts").status_code == 200


def test_roles_without_the_permission_are_refused(app) -> None:
    assert staff_client(app, "cashier").get("/admin/languages").status_code == 403
    assert staff_client(app, "kitchen").get("/admin/languages/texts").status_code == 403


def test_dashboard_warns_about_untranslated_dishes(app, two_dishes) -> None:
    page = staff_client(app, "manager").get("/admin/dashboard").get_data(as_text=True)
    assert "۱ غذا ترجمه‌ی انگلیسی ندارد" in page
