"""Choosing the right translation row for a language, with the Persian fallback."""

from collections.abc import Iterable

from restaurant.constants import DEFAULT_LANGUAGE_CODE


def pick_translation(translations: Iterable, language_code: str):  # noqa: ANN201
    """Return the text row in `language_code`, else Persian, else any row, else None.

    Every translation row carries its `language` (loaded with it), so the code
    is read from there.
    """
    by_code = {translation.language.code: translation for translation in translations}
    for code in (language_code, DEFAULT_LANGUAGE_CODE):
        if code in by_code:
            return by_code[code]
    return next(iter(by_code.values()), None)


def exact_translation(translations: Iterable, language_code: str):  # noqa: ANN201
    """Return the row written in exactly this language, or None (no fallback)."""
    for translation in translations:
        if translation.language.code == language_code:
            return translation
    return None
