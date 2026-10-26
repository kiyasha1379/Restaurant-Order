"""Language rules: which languages exist, which are on, and how they are written."""

from dataclasses import dataclass

from restaurant.constants import LANGUAGE_CODE_PERSIAN, SUPPORTED_LANGUAGE_CODES, TextDirection
from restaurant.repositories import LanguageRepository


@dataclass(frozen=True)
class LanguageInfo:
    """What a template needs to know about one language."""

    code: str
    name: str
    direction: TextDirection
    is_default: bool = False
    is_enabled: bool = True


# Persian is the fallback of the whole site and can never be switched off, so
# an empty or half-seeded database still renders a right-to-left page.
FALLBACK_LANGUAGE = LanguageInfo(
    code=LANGUAGE_CODE_PERSIAN, name="فارسی", direction=TextDirection.RTL, is_default=True
)


class LanguageService:
    """Decides the active language from the `languages` table."""

    def __init__(self, language_repository: LanguageRepository) -> None:
        """Receive the repository instead of importing it, so tests can swap it."""
        self._language_repository = language_repository

    @staticmethod
    def is_supported_code(code: str) -> bool:
        """Return True for the two language codes the site knows ('fa', 'en')."""
        return code in SUPPORTED_LANGUAGE_CODES

    def get_default_language(self) -> LanguageInfo:
        """Return the default language, or Persian when the table has no default."""
        language = self._language_repository.get_default()
        return self._to_info(language) if language else FALLBACK_LANGUAGE

    def get_available_language(self, code: str) -> LanguageInfo | None:
        """Return the language with this code if visitors may use it, else None.

        English can be switched off; Persian is always available.
        """
        language = self._language_repository.get_by_code(code)
        if language is None:
            return FALLBACK_LANGUAGE if code == LANGUAGE_CODE_PERSIAN else None
        if not language.is_enabled and code != LANGUAGE_CODE_PERSIAN:
            return None
        return self._to_info(language)

    def get_language(self, code: str) -> LanguageInfo | None:
        """Return the language with this code even when it is switched off (for the admin panel)."""
        language = self._language_repository.get_by_code(code)
        if language is None:
            return FALLBACK_LANGUAGE if code == LANGUAGE_CODE_PERSIAN else None
        return self._to_info(language)

    def list_available_languages(self) -> list[LanguageInfo]:
        """Return every language visitors may use, the default one first."""
        languages = [
            self._to_info(language)
            for language in self._language_repository.list_ordered()
            if language.is_enabled or language.code == LANGUAGE_CODE_PERSIAN
        ]
        return languages or [FALLBACK_LANGUAGE]

    @staticmethod
    def _to_info(language) -> LanguageInfo:  # noqa: ANN001 - a Language model row
        """Copy a row into an immutable value that is safe to keep after the session ends."""
        return LanguageInfo(
            code=language.code,
            name=language.name,
            direction=language.direction,
            is_default=language.is_default,
            is_enabled=language.is_enabled,
        )
