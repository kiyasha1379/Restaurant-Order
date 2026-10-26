"""Interface texts: lookup with fallback, missing-text report, and default sync."""

from collections.abc import Mapping
from dataclasses import dataclass, field

from restaurant.constants import DEFAULT_LANGUAGE_CODE, SUPPORTED_LANGUAGE_CODES
from restaurant.default_texts import DEFAULT_TEXTS
from restaurant.repositories import LanguageRepository, UiStringRepository

Texts = Mapping[str, Mapping[str, str]]


@dataclass(frozen=True)
class Translator:
    """Looks up texts for one language. Templates call it as `t("key")`.

    Lookup order for a key (technical plan, section 4):
    stored text in the language, default text in the language,
    stored Persian text, default Persian text, and finally the key itself.
    """

    language_code: str
    stored_texts: Texts = field(default_factory=dict)
    default_texts: Texts = field(default_factory=lambda: DEFAULT_TEXTS)

    def translate(self, key: str, **placeholders: object) -> str:
        """Return the text for `key`; `{name}` placeholders are filled from `placeholders`."""
        text = self._find(key)
        return text.format_map(placeholders) if placeholders else text

    __call__ = translate

    def _find(self, key: str) -> str:
        """Walk the fallback order described in the class docstring."""
        for language_code in (self.language_code, DEFAULT_LANGUAGE_CODE):
            stored = self.stored_texts.get(language_code, {}).get(key)
            if stored:
                return stored
            default = self.default_texts.get(key, {}).get(language_code)
            if default:
                return default
        return key


@dataclass(frozen=True)
class SyncReport:
    """What `sync_defaults` added to the database."""

    added_keys: int
    added_texts: int


class TranslationService:
    """Builds translators and keeps the stored texts in step with the defaults."""

    def __init__(
        self, ui_string_repository: UiStringRepository, language_repository: LanguageRepository
    ) -> None:
        """Receive the repositories instead of importing them, so tests can swap them."""
        self._ui_string_repository = ui_string_repository
        self._language_repository = language_repository

    def build_translator(self, language_code: str) -> Translator:
        """Load the stored texts for the language (and Persian) and wrap them in a Translator."""
        codes = {language_code, DEFAULT_LANGUAGE_CODE}
        return Translator(language_code, self._ui_string_repository.get_texts(codes))

    def find_missing_keys(self, language_code: str) -> list[str]:
        """List keys that have no text in this language, neither stored nor default."""
        stored = self._ui_string_repository.get_texts([language_code]).get(language_code, {})
        all_keys = set(DEFAULT_TEXTS) | set(self._ui_string_repository.list_keys())
        return sorted(
            key
            for key in all_keys
            if not stored.get(key) and not DEFAULT_TEXTS.get(key, {}).get(language_code)
        )

    def sync_defaults(self) -> SyncReport:
        """Copy default texts that are not in the database yet. Edited texts are never changed.

        The caller commits.
        """
        existing_keys = set(self._ui_string_repository.list_keys())
        stored = self._ui_string_repository.get_texts(SUPPORTED_LANGUAGE_CODES)
        added_keys = 0
        added_texts = 0
        for language in self._language_repository.list_all():
            for key, texts in DEFAULT_TEXTS.items():
                default_text = texts.get(language.code)
                if not default_text or stored.get(language.code, {}).get(key):
                    continue
                self._ui_string_repository.save_text(key, language, default_text)
                added_texts += 1
                if key not in existing_keys:
                    existing_keys.add(key)
                    added_keys += 1
        return SyncReport(added_keys=added_keys, added_texts=added_texts)
