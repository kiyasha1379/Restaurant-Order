"""Service rules, tested with fake repositories (constructor injection)."""

from restaurant.constants import DEFAULT_BRAND_NAME, TextDirection
from restaurant.services import FALLBACK_LANGUAGE, LanguageService, SiteSettingsService


class FakeLanguageRepository:
    """Returns a prepared language, or None to mimic an empty table."""

    def __init__(self, language):
        self._language = language

    def get_default(self):
        return self._language


class FakeSettingRepository:
    """Returns prepared values by key."""

    def __init__(self, values):
        self._values = values

    def get_value(self, key):
        return self._values.get(key)


class FakeLanguage:
    code = "en"
    name = "English"
    direction = TextDirection.LTR
    is_default = True
    is_enabled = True


def test_default_language_comes_from_the_repository():
    info = LanguageService(FakeLanguageRepository(FakeLanguage())).get_default_language()
    assert (info.code, info.direction) == ("en", TextDirection.LTR)


def test_empty_language_table_falls_back_to_persian_rtl():
    info = LanguageService(FakeLanguageRepository(None)).get_default_language()
    assert info == FALLBACK_LANGUAGE
    assert info.direction is TextDirection.RTL


def test_brand_name_uses_stored_value():
    service = SiteSettingsService(FakeSettingRepository({"brand_name": "Saffron"}))
    assert service.get_brand_name() == "Saffron"


def test_brand_name_falls_back_to_default():
    assert SiteSettingsService(FakeSettingRepository({})).get_brand_name() == DEFAULT_BRAND_NAME
