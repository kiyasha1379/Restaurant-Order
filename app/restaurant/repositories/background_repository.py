"""Queries for the `backgrounds` table."""

from sqlalchemy import select

from restaurant.models import Background
from restaurant.repositories.base import BaseRepository


class BackgroundRepository(BaseRepository[Background]):
    """Reads video/poster backgrounds by their key."""

    model = Background

    def get_by_key(self, key: str) -> Background | None:
        """Return the background with this key, or None."""
        return self._session.scalar(select(Background).where(Background.key == key))
