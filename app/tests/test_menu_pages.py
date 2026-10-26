"""Home and menu pages, the background macro and the navigation."""

import pytest

from restaurant.extensions import db
from restaurant.models import Background
from restaurant.service_factory import make_demo_seed_service


@pytest.fixture
def seeded(app):
    make_demo_seed_service().seed()
    db.session.commit()


def test_menu_page_lists_dishes_in_persian(client, seeded):
    html = client.get("/fa/menu").get_data(as_text=True)
    assert "کباب کوبیده" in html
    assert 'class="dish-card"' in html
    assert "۲۸۰٬۰۰۰" in html


def test_menu_page_lists_dishes_in_english(client, seeded):
    html = client.get("/en/menu").get_data(as_text=True)
    assert "Koobideh Kebab" in html
    assert "280,000" in html
    assert 'dir="ltr"' in html


def test_menu_chips_name_every_category(client, seeded):
    html = client.get("/fa/menu").get_data(as_text=True)
    for name in ("همه", "کباب‌ها", "پیتزا", "نوشیدنی‌ها"):
        assert name in html


def test_category_query_hides_other_categories_without_javascript(client, seeded):
    html = client.get("/fa/menu?category=pizza").get_data(as_text=True)
    assert 'data-category="kebab" hidden' in html
    assert 'data-category="pizza" hidden' not in html


def test_unknown_category_shows_everything(client, seeded):
    html = client.get("/fa/menu?category=nope").get_data(as_text=True)
    assert "dish-grid__item" in html
    assert 'data-category="kebab" hidden' not in html
    assert 'data-category="pizza" hidden' not in html


def test_empty_menu_shows_a_message(client):
    assert "هنوز غذایی" in client.get("/fa/menu").get_data(as_text=True)


def test_dish_has_details_on_the_back_and_an_add_button(client, seeded):
    html = client.get("/fa/menu").get_data(as_text=True)
    assert "مواد اصلی:" in html
    assert "data-add-dish=" in html
    assert 'aria-label="افزودن کباب کوبیده به سبد"' in html


def test_numbers_follow_the_page_language_on_every_request(client, seeded):
    """A filter on a constant must never be frozen into the compiled template."""
    persian = client.get("/fa/menu").get_data(as_text=True)
    english = client.get("/en/menu").get_data(as_text=True)
    persian_again = client.get("/fa/menu").get_data(as_text=True)
    assert "<bdi>۰</bdi>" in persian and "<bdi>۰</bdi>" in persian_again
    assert "<bdi>0</bdi>" in english


def test_home_shows_chefs_picks_and_all_sections(client, seeded):
    html = client.get("/fa/").get_data(as_text=True)
    for section in ("top", "modes", "dishes", "how", "contact"):
        assert f'id="{section}"' in html
    assert "جوجه‌کباب زعفرانی" in html
    assert "سفره‌ای گرم" in html


def test_home_works_without_any_menu_data(client):
    html = client.get("/fa/").get_data(as_text=True)
    assert 'id="dishes"' not in html
    assert 'id="how"' in html


def test_home_in_english(client, seeded):
    html = client.get("/en/").get_data(as_text=True)
    assert "A warm table" in html
    assert "Chef&#39;s picks" in html or "Chef's picks" in html


def test_the_account_pages_are_linked_from_the_menus(client):
    html = client.get("/fa/").get_data(as_text=True)
    assert "/fa/menu" in html
    assert 'href="/fa/login"' in html
    assert 'href="/fa/account"' in html
    assert 'href="/fa/contact"' in html


def test_the_reservation_page_is_linked_from_the_menus_and_the_home_page(client):
    html = client.get("/fa/").get_data(as_text=True)
    assert 'href="/fa/reserve"' in html and 'id="reserve"' in html


def test_current_page_is_marked_in_the_navigation(client):
    html = client.get("/fa/menu").get_data(as_text=True)
    assert 'href="/fa/menu" aria-current="page"' in html


def test_background_uses_poster_and_lazy_video(client, seeded):
    html = client.get("/fa/").get_data(as_text=True)
    assert "data-lazy-video" in html
    assert 'data-src="/static/media/backgrounds/home-hero.mp4"' in html
    assert 'src="/static/media/backgrounds/home-hero.webp"' in html
    # The video file is never loaded up front.
    assert 'preload="none"' in html
    assert ' src="/static/media/backgrounds/home-hero.mp4"' not in html
    assert 'data-mobile-mode="poster_only"' in html


def test_missing_background_row_draws_the_gradient(client):
    html = client.get("/fa/menu").get_data(as_text=True)
    assert 'class="bg"' in html
    assert "<video" not in html


def test_disabled_background_is_not_drawn(app, client, seeded):
    db.session.query(Background).filter_by(key="menu-page").one().is_enabled = False
    db.session.commit()
    html = client.get("/fa/menu").get_data(as_text=True)
    assert "<video" not in html


def test_background_without_a_video_still_shows_the_poster(app, client, seeded):
    row = db.session.query(Background).filter_by(key="menu-page").one()
    row.video_path = None
    db.session.commit()
    html = client.get("/fa/menu").get_data(as_text=True)
    assert "home-dishes.webp" in html
    assert "<video" not in html


def test_phone_tab_bar_and_header_cart_are_present(client):
    html = client.get("/fa/").get_data(as_text=True)
    assert 'class="tab-bar"' in html
    assert "data-cart-count" in html
