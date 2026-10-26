"""Queries for the `ui_strings` and `ui_string_translations` tables."""

from collections.abc import Iterable

from sqlalchemy import select

from restaurant.models import Language, UiString, UiStringTranslation
from restaurant.repositories.base import BaseRepository


class UiStringRepository(BaseRepository[UiString]):
    """Reads and writes editable interface texts."""

    model = UiString

    def get_texts(self, language_codes: Iterable[str]) -> dict[str, dict[str, str]]:
        """Return {language_code: {key: text}} for the given languages (empty texts skipped)."""
        statement = (
            select(Language.code, UiString.key, UiStringTranslation.text)
            .join(UiStringTranslation, UiStringTranslation.ui_string_id == UiString.id)
            .join(Language, Language.id == UiStringTranslation.language_id)
            .where(Language.code.in_(list(language_codes)))
        )
        texts: dict[str, dict[str, str]] = {}
        for language_code, key, text in self._session.execute(statement):
            if text:
                texts.setdefault(language_code, {})[key] = text
        return texts

    def list_keys(self) -> list[str]:
        """Return every stored key in alphabetical order."""
        return list(self._session.scalars(select(UiString.key).order_by(UiString.key)))

    def get_by_key(self, key: str) -> UiString | None:
        """Return the string row for `key`, or None."""
        return self._session.scalar(select(UiString).where(UiString.key == key))

    def get_translation(
        self, ui_string: UiString, language: Language
    ) -> UiStringTranslation | None:
        """Return the text of `ui_string` in `language`, or None."""
        return self._session.get(UiStringTranslation, (ui_string.id, language.id))

    def save_text(self, key: str, language: Language, text: str) -> UiStringTranslation:
        """Create or update one text. The caller commits."""
        ui_string = self.get_by_key(key)
        if ui_string is None:
            ui_string = self.add(UiString(key=key))
            self._session.flush()
        translation = self.get_translation(ui_string, language)
        if translation is None:
            translation = UiStringTranslation(
                ui_string=ui_string, language_id=language.id, text=text
            )
            self._session.add(translation)
        else:
            translation.text = text
        return translation
