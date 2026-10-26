"""Repository reads and writes."""

from restaurant.extensions import db
from restaurant.models import Background
from restaurant.repositories import BackgroundRepository, LanguageRepository, SettingRepository


def test_language_repository_finds_default_and_by_code(app):
    repository = LanguageRepository(db.session)
    assert repository.get_default().code == "fa"
    assert repository.get_by_code("en").name == "English"
    assert repository.get_by_code("de") is None
    assert len(repository.list_all()) == 2


def test_setting_repository_creates_then_updates(app):
    repository = SettingRepository(db.session)
    assert repository.get_value("brand_name") is None

    repository.set_value("brand_name", "Saffron")
    db.session.commit()
    assert repository.get_value("brand_name") == "Saffron"

    repository.set_value("brand_name", "Ember")
    db.session.commit()
    assert repository.get_value("brand_name") == "Ember"


def test_background_repository_finds_by_key(app):
    repository = BackgroundRepository(db.session)
    repository.add(Background(key="home-hero"))
    db.session.commit()
    assert repository.get_by_key("home-hero") is not None
    assert repository.get_by_key("missing") is None
