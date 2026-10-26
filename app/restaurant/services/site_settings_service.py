"""Site-wide settings with sensible defaults."""

import re
from dataclasses import dataclass

from restaurant.constants import (
    DEFAULT_BRAND_NAME,
    DEFAULT_DELIVERY_FEE,
    DEFAULT_RESERVATION_DURATION_MINUTES,
    DEFAULT_RESERVATION_MAX_ADVANCE_DAYS,
    DEFAULT_RESERVATION_MIN_NOTICE_MINUTES,
    DEFAULT_RESERVATION_SLOT_MINUTES,
    SettingKey,
)
from restaurant.repositories import SettingRepository

MAX_DELIVERY_FEE = 10_000_000
BRAND_NAME_MAX_LENGTH = 60
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

# Allowed ranges for the reservation rules; anything outside falls back to the default.
MAX_ADVANCE_DAYS_RANGE = (1, 365)
DURATION_MINUTES_RANGE = (30, 480)
SLOT_MINUTES_RANGE = (15, 120)
MIN_NOTICE_MINUTES_RANGE = (0, 1440)


@dataclass(frozen=True)
class BookingRules:
    """How reservations work: how far ahead, how long, which start times, who confirms."""

    max_advance_days: int = DEFAULT_RESERVATION_MAX_ADVANCE_DAYS
    duration_minutes: int = DEFAULT_RESERVATION_DURATION_MINUTES
    slot_minutes: int = DEFAULT_RESERVATION_SLOT_MINUTES
    min_notice_minutes: int = DEFAULT_RESERVATION_MIN_NOTICE_MINUTES
    auto_confirm: bool = False


@dataclass(frozen=True)
class OrderingSettings:
    """How online orders work: the delivery fee, the payment methods on offer and the pause."""

    delivery_fee: int = DEFAULT_DELIVERY_FEE
    online_payment: bool = True
    cash_payment: bool = True
    paused: bool = False


@dataclass(frozen=True)
class SiteLook:
    """What every page needs to look like this restaurant: name, logo and accent colour."""

    brand_name: str = DEFAULT_BRAND_NAME
    logo_path: str | None = None
    accent_color: str | None = None


class InvalidSettingError(ValueError):
    """A setting value was refused. `field` names the form field and `problem` says why."""

    def __init__(self, field: str, problem: str) -> None:
        """Keep the field and the reason so the form can show a message in the page language."""
        super().__init__(f"{field}: {problem}")
        self.field = field
        self.problem = problem


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

    def get_site_look(self) -> SiteLook:
        """Return the brand name, logo and accent colour (a bad stored colour is ignored)."""
        color = self._setting_repository.get_value(SettingKey.ACCENT_COLOR)
        return SiteLook(
            brand_name=self.get_brand_name(),
            logo_path=self._setting_repository.get_value(SettingKey.LOGO_PATH) or None,
            accent_color=color if color and HEX_COLOR.match(color) else None,
        )

    def set_brand(self, brand_name: str, accent_color: str | None) -> None:
        """Store the brand name and the accent colour ("" or None restores the default colour).

        The caller commits. Raises InvalidSettingError.
        """
        brand_name = brand_name.strip()
        if not 1 <= len(brand_name) <= BRAND_NAME_MAX_LENGTH:
            raise InvalidSettingError("brand_name", "length")
        color = (accent_color or "").strip()
        if color and not HEX_COLOR.match(color):
            raise InvalidSettingError("accent_color", "format")
        self._setting_repository.set_value(SettingKey.BRAND_NAME, brand_name)
        self._setting_repository.set_value(SettingKey.ACCENT_COLOR, color.lower())

    def get_logo_path(self) -> str | None:
        """Return the stored logo address (relative to the static folder), or None."""
        return self._setting_repository.get_value(SettingKey.LOGO_PATH) or None

    def set_logo_path(self, path: str | None) -> None:
        """Remember the logo, or forget it with None. The caller commits."""
        self._setting_repository.set_value(SettingKey.LOGO_PATH, path or "")

    def get_ordering_settings(self) -> OrderingSettings:
        """Return how online orders work now; a missing value uses its default."""
        read = self._setting_repository.get_value
        return OrderingSettings(
            delivery_fee=self.get_delivery_fee(),
            online_payment=read(SettingKey.ONLINE_PAYMENT_ENABLED) != "0",
            cash_payment=read(SettingKey.CASH_PAYMENT_ENABLED) != "0",
            paused=read(SettingKey.ORDERING_PAUSED) == "1",
        )

    def set_ordering_settings(self, settings: OrderingSettings) -> None:
        """Store the ordering settings. The caller commits. Raises InvalidSettingError."""
        if not 0 <= settings.delivery_fee <= MAX_DELIVERY_FEE:
            raise InvalidSettingError("delivery_fee", "range")
        if not settings.online_payment and not settings.cash_payment:
            raise InvalidSettingError("payment", "none_enabled")
        write = self._setting_repository.set_value
        write(SettingKey.DELIVERY_FEE, str(settings.delivery_fee))
        write(SettingKey.ONLINE_PAYMENT_ENABLED, "1" if settings.online_payment else "0")
        write(SettingKey.CASH_PAYMENT_ENABLED, "1" if settings.cash_payment else "0")
        write(SettingKey.ORDERING_PAUSED, "1" if settings.paused else "0")

    def is_ordering_paused(self) -> bool:
        """Return True while the restaurant has paused online ordering."""
        return self._setting_repository.get_value(SettingKey.ORDERING_PAUSED) == "1"

    def get_booking_rules(self) -> BookingRules:
        """Return the reservation rules; a missing or broken value uses its default."""
        defaults = BookingRules()
        return BookingRules(
            max_advance_days=self._read_int(
                SettingKey.RESERVATION_MAX_ADVANCE_DAYS,
                defaults.max_advance_days,
                MAX_ADVANCE_DAYS_RANGE,
            ),
            duration_minutes=self._read_int(
                SettingKey.RESERVATION_DURATION_MINUTES,
                defaults.duration_minutes,
                DURATION_MINUTES_RANGE,
            ),
            slot_minutes=self._read_int(
                SettingKey.RESERVATION_SLOT_MINUTES, defaults.slot_minutes, SLOT_MINUTES_RANGE
            ),
            min_notice_minutes=self._read_int(
                SettingKey.RESERVATION_MIN_NOTICE_MINUTES,
                defaults.min_notice_minutes,
                MIN_NOTICE_MINUTES_RANGE,
            ),
            auto_confirm=self._setting_repository.get_value(SettingKey.RESERVATION_AUTO_CONFIRM)
            == "1",
        )

    def set_booking_rules(self, rules: BookingRules) -> None:
        """Store the reservation rules. The caller commits."""
        stored = {
            SettingKey.RESERVATION_MAX_ADVANCE_DAYS: str(rules.max_advance_days),
            SettingKey.RESERVATION_DURATION_MINUTES: str(rules.duration_minutes),
            SettingKey.RESERVATION_SLOT_MINUTES: str(rules.slot_minutes),
            SettingKey.RESERVATION_MIN_NOTICE_MINUTES: str(rules.min_notice_minutes),
            SettingKey.RESERVATION_AUTO_CONFIRM: "1" if rules.auto_confirm else "0",
        }
        for key, value in stored.items():
            self._setting_repository.set_value(key, value)

    def _read_int(self, key: SettingKey, default: int, allowed: tuple[int, int]) -> int:
        """Read a whole-number setting inside its allowed range, or return the default."""
        raw = self._setting_repository.get_value(key)
        try:
            value = int(raw) if raw is not None else default
        except ValueError:
            return default
        return value if allowed[0] <= value <= allowed[1] else default
