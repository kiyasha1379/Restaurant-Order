"""Menu data layer: repositories, service fallback and the demo seed."""

import pytest

from restaurant.extensions import db
from restaurant.models import Language
from restaurant.repositories import CategoryRepository, DishRepository
from restaurant.seed.demo_data import DEMO_BACKGROUNDS, DEMO_CATEGORIES
from restaurant.service_factory import make_demo_seed_service, make_menu_service
from restaurant.services import MenuService
from tests.helpers import add_category, add_dish


def test_dish_uses_the_requested_language(app):
    category = add_category("pizza", {"fa": "پیتزا", "en": "Pizza"})
    add_dish(category, {"fa": "مارگاریتا", "en": "Margherita"}, base_price=260_000)
    db.session.commit()

    service = make_menu_service()
    assert service.list_dishes("en")[0].name == "Margherita"
    assert service.list_dishes("fa")[0].name == "مارگاریتا"
    assert service.list_dishes("en")[0].price == 260_000


def test_missing_english_text_falls_back_to_persian(app):
    category = add_category("pizza", {"fa": "پیتزا"})
    add_dish(category, {"fa": "مارگاریتا"})
    db.session.commit()

    service = make_menu_service()
    assert service.list_dishes("en")[0].name == "مارگاریتا"
    assert service.list_categories("en")[0].name == "پیتزا"


def test_hidden_dishes_and_hidden_categories_are_not_listed(app):
    shown = add_category("a", {"fa": "الف"})
    hidden = add_category("b", {"fa": "ب"}, is_visible=False)
    add_dish(shown, {"fa": "یک"})
    add_dish(shown, {"fa": "دو"}, is_visible=False)
    add_dish(hidden, {"fa": "سه"})
    db.session.commit()

    service = make_menu_service()
    assert [dish.name for dish in service.list_dishes("fa")] == ["یک"]
    assert [category.slug for category in service.list_categories("fa")] == ["a"]
    assert service.has_category("a") and not service.has_category("b")
    assert not service.has_category("missing")


def test_menu_order_follows_sort_order(app):
    second = add_category("second", {"fa": "دوم"}, sort_order=2)
    first = add_category("first", {"fa": "اول"}, sort_order=1)
    add_dish(second, {"fa": "ج"}, sort_order=0)
    add_dish(first, {"fa": "ب"}, sort_order=2)
    add_dish(first, {"fa": "الف"}, sort_order=1)
    db.session.commit()

    names = [dish.name for dish in make_menu_service().list_dishes("fa")]
    assert names == ["الف", "ب", "ج"]


def test_chefs_picks_are_limited_and_filtered(app):
    category = add_category("a", {"fa": "الف"})
    for index in range(5):
        add_dish(category, {"fa": f"غذا {index}"}, is_chefs_pick=index < 3)
    db.session.commit()

    assert len(make_menu_service().list_chefs_picks("fa", limit=2)) == 2
    assert len(make_menu_service().list_chefs_picks("fa", limit=10)) == 3


def test_list_dishes_can_be_narrowed_to_one_category(app):
    first = add_category("a", {"fa": "الف"})
    second = add_category("b", {"fa": "ب"})
    add_dish(first, {"fa": "یک"})
    add_dish(second, {"fa": "دو"})
    db.session.commit()

    assert [d.name for d in make_menu_service().list_dishes("fa", "b")] == ["دو"]


def test_service_works_with_fake_repositories():
    class FakeCategoryRepository:
        def list_visible(self):
            return []

    class FakeDishRepository:
        def list_chefs_picks(self, limit):
            return []

    service = MenuService(FakeCategoryRepository(), FakeDishRepository())
    assert service.list_categories("fa") == []
    assert service.list_chefs_picks("fa") == []


def test_repositories_are_built_on_the_session(app):
    assert CategoryRepository(db.session).list_visible() == []
    assert DishRepository(db.session).list_visible() == []


def test_seed_adds_the_demo_content_once(app):
    first = make_demo_seed_service().seed()
    db.session.commit()
    assert first.backgrounds == len(DEMO_BACKGROUNDS)
    assert first.categories == len(DEMO_CATEGORIES)
    assert first.dishes == sum(len(c.dishes) for c in DEMO_CATEGORIES)

    second = make_demo_seed_service().seed()
    assert (second.backgrounds, second.categories, second.dishes) == (0, 0, 0)


def test_seeded_dishes_have_both_languages(app):
    make_demo_seed_service().seed()
    db.session.commit()
    english = make_menu_service().list_dishes("en")
    persian = make_menu_service().list_dishes("fa")
    assert len(english) == len(persian) > 0
    assert all(dish.name and dish.ingredients and dish.serving_note for dish in english)
    assert english[0].name != persian[0].name


def test_seed_needs_the_languages(app):
    db.session.query(Language).delete()
    db.session.commit()
    with pytest.raises(RuntimeError, match="flask db upgrade"):
        make_demo_seed_service().seed()


def test_every_seeded_background_file_exists(app):
    from pathlib import Path

    static_folder = Path(app.static_folder)
    for background in DEMO_BACKGROUNDS:
        assert (static_folder / background.video_path).is_file(), background.video_path
        assert (static_folder / background.poster_path).is_file(), background.poster_path
