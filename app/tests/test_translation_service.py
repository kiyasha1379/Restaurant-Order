"""Text lookup order, missing-text report and default sync."""

from restaurant.extensions import db
from restaurant.models import Language
from restaurant.repositories import LanguageRepository, UiStringRepository
from restaurant.service_factory import make_translation_service
from restaurant.services import Translator

DEFAULTS = {"greet": {"fa": "سلام", "en": "Hello"}, "only.fa": {"fa": "فقط فارسی"}}


def test_translator_prefers_the_stored_text_over_the_default():
    translator = Translator("en", {"en": {"greet": "Hi"}}, DEFAULTS)
    assert translator("greet") == "Hi"


def test_translator_uses_the_default_in_the_same_language_before_persian_storage():
    translator = Translator("en", {"fa": {"greet": "درود"}}, DEFAULTS)
    assert translator("greet") == "Hello"


def test_translator_falls_back_to_persian_then_to_the_key():
    translator = Translator("en", {}, DEFAULTS)
    assert translator("only.fa") == "فقط فارسی"
    assert translator("unknown.key") == "unknown.key"


def test_placeholders_are_filled():
    translator = Translator("en", {}, {"hello": {"en": "Hello {name}"}})
    assert translator("hello", name="Sara") == "Hello Sara"


def test_sync_adds_defaults_once_and_never_overwrites_edits(app):
    service = make_translation_service()
    first = service.sync_defaults()
    db.session.commit()
    assert first.added_keys > 0
    assert first.added_texts >= first.added_keys

    english = LanguageRepository(db.session).get_by_code("en")
    UiStringRepository(db.session).save_text("home.cta", english, "Browse the menu")
    db.session.commit()

    second = make_translation_service().sync_defaults()
    db.session.commit()
    assert (second.added_keys, second.added_texts) == (0, 0)
    stored = UiStringRepository(db.session).get_texts(["en"])
    assert stored["en"]["home.cta"] == "Browse the menu"


def test_stored_text_reaches_the_translator(app):
    english = db.session.query(Language).filter_by(code="en").one()
    UiStringRepository(db.session).save_text("home.cta", english, "Browse the menu")
    db.session.commit()
    assert make_translation_service().build_translator("en")("home.cta") == "Browse the menu"


def test_empty_stored_text_counts_as_missing(app):
    english = db.session.query(Language).filter_by(code="en").one()
    UiStringRepository(db.session).save_text("custom.key", english, "")
    db.session.commit()
    assert "custom.key" in make_translation_service().find_missing_keys("en")
    assert make_translation_service().build_translator("en")("custom.key") == "custom.key"
