"""Site-wide settings with sensible defaults."""

from restaurant.constants import DEFAULT_BRAND_NAME, DEFAULT_DELIVERY_FEE, SettingKey
from restaurant.repositories import SettingRepository


class SiteSettingsService:
    """Reads settings that every page needs, such as the brand name."""

    def __init__(self, setting_repository: SettingRepository) -> None:
        """Receive the repository instead of importing it, so tests can swap it."""
        self._setting_repository = setting_repository

    def get_brand_name(self) -> str:
        """Return the brand name, or a neutral default before it is configured."""
        stored_name = self._setting_repository.get_value(SettingKey.BRAND_NAME)
        return stored_name or DEFAULT_BRAND_NAME

    def get_delivery_fee(self) -> int:
        """Return the fixed delivery fee in tomans; a missing or broken value uses the default."""
        stored_fee = self._setting_repository.get_value(SettingKey.DELIVERY_FEE)
        try:
            fee = int(stored_fee) if stored_fee is not None else DEFAULT_DELIVERY_FEE
        except ValueError:
            return DEFAULT_DELIVERY_FEE
        return fee if fee >= 0 else DEFAULT_DELIVERY_FEE
