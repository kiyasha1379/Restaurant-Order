"""Home page, direction handling, language routes, demo bar and error pages."""

from flask import Flask

from restaurant import create_app
from restaurant.extensions import db
from restaurant.models import Language, Setting


def set_language_enabled(code: str, is_enabled: bool) -> None:
    """Switch a language on or off, like the admin panel will."""
    db.session.query(Language).filter_by(code=code).one().is_enabled = is_enabled
    db.session.commit()


def make_english_default() -> None:
    """Flip the default language to English."""
    for language in db.session.query(Language):
        language.is_default = language.code == "en"
    db.session.commit()


def test_bare_address_redirects_to_the_default_language(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/fa/")


def test_bare_address_follows_a_changed_default_language(app, client):
    make_english_default()
    assert client.get("/").headers["Location"].endswith("/en/")


def test_persian_page_is_right_to_left(client):
    html = client.get("/fa/").get_data(as_text=True)
    assert '<html lang="fa" dir="rtl">' in html
    assert "سفره‌ای گرم" in html


def test_english_page_is_left_to_right(client):
    html = client.get("/en/").get_data(as_text=True)
    assert '<html lang="en" dir="ltr">' in html
    assert "A warm table" in html


def test_the_same_page_opens_in_both_languages(client):
    assert client.get("/fa/").status_code == 200
    assert client.get("/en/").status_code == 200


def test_unknown_language_prefix_is_a_404(client):
    assert client.get("/de/").status_code == 404


def test_switching_english_off_redirects_to_persian(app, client):
    set_language_enabled("en", False)
    response = client.get("/en/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/fa/")


def test_the_switcher_links_to_the_other_language(client):
    html = client.get("/fa/").get_data(as_text=True)
    assert 'href="/en/"' in html
    assert 'class="lang-switch"' in html
    english_html = client.get("/en/").get_data(as_text=True)
    assert 'href="/fa/"' in english_html


def test_the_switcher_disappears_when_english_is_off(app, client):
    set_language_enabled("en", False)
    assert 'class="lang-switch"' not in client.get("/fa/").get_data(as_text=True)


def test_the_page_uses_stored_brand_name(app, client):
    db.session.add(Setting(key="brand_name", value="Saffron House"))
    db.session.commit()
    assert "Saffron House" in client.get("/fa/").get_data(as_text=True)


def test_styles_load_in_the_planned_order(client):
    html = client.get("/fa/").get_data(as_text=True)
    positions = [html.index(name) for name in ("fonts.css", "tokens.css", "base.css", "home.css")]
    assert positions == sorted(positions)


def test_demo_bar_is_hidden_outside_demo_mode(client):
    assert 'class="demo-bar"' not in client.get("/fa/").get_data(as_text=True)


def test_demo_bar_is_shown_in_demo_mode():
    app = create_app("test", {"DEMO_MODE": True})
    with app.app_context():
        db.create_all()
        html = app.test_client().get("/fa/").get_data(as_text=True)
    assert 'class="demo-bar"' in html


def test_404_page_follows_the_language_of_the_address(client):
    persian = client.get("/fa/no-such-page")
    english = client.get("/en/no-such-page")
    assert persian.status_code == english.status_code == 404
    assert "صفحه پیدا نشد" in persian.get_data(as_text=True)
    assert "Page not found" in english.get_data(as_text=True)
    assert 'dir="ltr"' in english.get_data(as_text=True)


def test_server_error_shows_the_500_page(app: Flask):
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/boom")
    def boom() -> str:
        raise RuntimeError("test failure")

    response = app.test_client().get("/boom")
    assert response.status_code == 500
    assert "مشکلی پیش آمد" in response.get_data(as_text=True)


def test_page_still_renders_when_the_database_is_missing():
    """Before `flask db upgrade` the tables do not exist; pages must not crash."""
    app = create_app("test")
    with app.app_context():
        response = app.test_client().get("/fa/")
    assert response.status_code == 200
    assert '<html lang="fa" dir="rtl">' in response.get_data(as_text=True)
