"""Queries for the `site_sections` table."""

from sqlalchemy import select

from restaurant.models import SiteSection
from restaurant.repositories.base import BaseRepository


class SiteSectionRepository(BaseRepository[SiteSection]):
    """Reads and writes the order and visibility of the home sections."""

    model = SiteSection

    def list_ordered(self) -> list[SiteSection]:
        """Return the stored sections from first to last."""
        return list(self._session.scalars(select(SiteSection).order_by(SiteSection.position)))

    def save(self, key: str, position: int, is_visible: bool) -> SiteSection:
        """Create the section row or update it. The caller commits."""
        section = self.get(key)
        if section is None:
            return self.add(SiteSection(key=key, position=position, is_visible=is_visible))
        section.position = position
        section.is_visible = is_visible
        return section
