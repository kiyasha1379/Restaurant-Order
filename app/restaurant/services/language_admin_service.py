"""Managing the two languages from the admin panel: status, switches and interface texts."""

import math
from collections.abc import Mapping
from dataclasses import dataclass

from restaurant.constants import (
    LANGUAGE_CODE_ENGLISH,
    LANGUAGE_CODE_PERSIAN,
    SUPPORTED_LANGUAGE_CODES,
)
from restaurant.default_texts import DEFAULT_TEXTS
from restaurant.repositories import (
    CategoryRepository,
    DishRepository,
    LanguageRepository,
    UiStringRepository,
)

TEXTS_PER_PAGE = 25
MAX_TEXT_LENGTH = 2000


class LanguageAdminError(ValueError):
    """A language setting was refused."""


class DefaultMustBeEnabledError(LanguageAdminError):
    """The default language cannot be switched off."""


@dataclass(frozen=True)
class Progress:
    """How many of some items have a text in one language."""

    done: int
    total: int

    @property
    def percent(self) -> int:
        """The share done, 0 to 100 (an empty set counts as complete)."""
        return 100 if self.total == 0 else self.done * 100 // self.total


@dataclass(frozen=True)
class LanguageStatus:
    """One language: its switches and how complete its translations are."""

    code: str
    name: str
    is_enabled: bool
    is_default: bool
    dishes: Progress
    categories: Progress
    texts: Progress


@dataclass(frozen=True)
class TextRow:
    """One interface text with what each language currently shows."""

    key: str
    texts: Mapping[str, str]


@dataclass(frozen=True)
class TextPage:
    """One page of the interface-text editor."""

    rows: list[TextRow]
    total: int
    page: int
    pages: int


class LanguageAdminService:
    """Reads translation progress and changes language switches and interface texts."""

    def __init__(
        self,
        language_repository: LanguageRepository,
        ui_string_repository: UiStringRepository,
        dish_repository: DishRepository,
        category_repository: CategoryRepository,
    ) -> None:
        """Receive the repositories instead of importing them, so tests can swap them."""
        self._languages = language_repository
        self._ui_strings = ui_string_repository
        self._dishes = dish_repository
        self._categories = category_repository

    def list_status(self) -> list[LanguageStatus]:
        """Return Persian and English with their switches and translation progress."""
        dish_total, category_total = self._dishes.count(), self._categories.count()
        all_keys = self._all_keys()
        statuses = []
        for language in self._languages.list_ordered():
            code = language.code
            statuses.append(
                LanguageStatus(
                    code=code,
                    name=language.name,
                    is_enabled=language.is_enabled,
                    is_default=language.is_default,
                    dishes=Progress(
                        dish_total - self._dishes.count_without_translation(code), dish_total
                    ),
                    categories=Progress(
                        category_total - self._categories.count_without_translation(code),
                        category_total,
                    ),
                    texts=Progress(len(all_keys) - len(self.missing_keys(code)), len(all_keys)),
                )
            )
        return statuses

    def update_settings(self, english_enabled: bool, default_code: str) -> None:
        """Switch English on or off and choose the default language. The caller commits.

        Persian is always on. Raises LanguageAdminError for an unknown code and
        DefaultMustBeEnabledError when the default would be switched off.
        """
        if default_code not in SUPPORTED_LANGUAGE_CODES:
            raise LanguageAdminError(default_code)
        if default_code == LANGUAGE_CODE_ENGLISH and not english_enabled:
            raise DefaultMustBeEnabledError(default_code)
        for language in self._languages.list_all():
            language.is_enabled = english_enabled or language.code == LANGUAGE_CODE_PERSIAN
            language.is_default = language.code == default_code

    def missing_keys(self, language_code: str) -> list[str]:
        """Return the keys that show no text in this language (stored or built-in)."""
        stored = self._ui_strings.get_texts([language_code]).get(language_code, {})
        return [
            key
            for key in self._all_keys()
            if not stored.get(key) and not DEFAULT_TEXTS.get(key, {}).get(language_code)
        ]

    def list_texts(self, query: str = "", missing_in: str | None = None, page: int = 1) -> TextPage:
        """Return one page of interface texts, optionally only those missing in a language."""
        stored = self._ui_strings.get_texts(SUPPORTED_LANGUAGE_CODES)
        needle = query.strip().lower()
        rows = []
        for key in self._all_keys():
            texts = {code: self._effective(stored, key, code) for code in SUPPORTED_LANGUAGE_CODES}
            if missing_in and texts.get(missing_in):
                continue
            if (
                needle
                and needle not in key.lower()
                and not any(needle in text.lower() for text in texts.values())
            ):
                continue
            rows.append(TextRow(key, texts))
        page = max(page, 1)
        start = (page - 1) * TEXTS_PER_PAGE
        return TextPage(
            rows[start : start + TEXTS_PER_PAGE],
            len(rows),
            page,
            max(math.ceil(len(rows) / TEXTS_PER_PAGE), 1),
        )

    def save_texts(self, entries: Mapping[str, Mapping[str, str]]) -> int:
        """Store the texts that differ from what is shown now; return how many were changed.

        Unknown keys and languages are ignored. An empty text goes back to the built-in
        text. The caller commits.
        """
        stored = self._ui_strings.get_texts(SUPPORTED_LANGUAGE_CODES)
        known_keys = set(self._all_keys())
        changed = 0
        for key, texts in entries.items():
            if key not in known_keys:
                continue
            for code, text in texts.items():
                language = self._languages.get_by_code(code)
                text = text.strip()[:MAX_TEXT_LENGTH]
                if language is None or text == self._effective(stored, key, code):
                    continue
                self._ui_strings.save_text(key, language, text)
                changed += 1
        return changed

    def _all_keys(self) -> list[str]:
        """Return every known key: built-in texts plus any stored ones."""
        return sorted(set(DEFAULT_TEXTS) | set(self._ui_strings.list_keys()))

    @staticmethod
    def _effective(stored: Mapping[str, Mapping[str, str]], key: str, code: str) -> str:
        """Return the text a language shows for a key: stored, else built-in, else empty."""
        return stored.get(code, {}).get(key) or DEFAULT_TEXTS.get(key, {}).get(code, "")
