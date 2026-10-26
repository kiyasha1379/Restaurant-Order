"""Queries for the `languages` table."""

from sqlalchemy import select

from restaurant.models import Language
from restaurant.repositories.base import BaseRepository


class LanguageRepository(BaseRepository[Language]):
    """Reads the two site languages."""

    model = Language

    def get_by_code(self, code: str) -> Language | None:
        """Return the language with this code ('fa' or 'en'), or None."""
        return self._session.scalar(select(Language).where(Language.code == code))

    def get_default(self) -> Language | None:
        """Return the language marked as default, or None on an empty table."""
        return self._session.scalar(select(Language).where(Language.is_default.is_(True)))

    def list_ordered(self) -> list[Language]:
        """Return both languages, the default one first."""
        statement = select(Language).order_by(Language.is_default.desc(), Language.id)
        return list(self._session.scalars(statement))
