"""Queries for the `settings` table."""

from restaurant.models import Setting
from restaurant.repositories.base import BaseRepository


class SettingRepository(BaseRepository[Setting]):
    """Reads and writes site-wide key/value settings."""

    model = Setting

    def get_value(self, key: str) -> str | None:
        """Return the stored value for `key`, or None when it was never set."""
        setting = self.get(key)
        return setting.value if setting else None

    def set_value(self, key: str, value: str) -> Setting:
        """Create the setting or update its value. The caller commits."""
        setting = self.get(key)
        if setting is None:
            return self.add(Setting(key=key, value=value))
        setting.value = value
        return setting
