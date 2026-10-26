"""The admin "Settings" page: ordering rules, payment methods and contact details."""

from dataclasses import dataclass

from restaurant.constants import SUPPORTED_LANGUAGE_CODES
from restaurant.default_texts import DEFAULT_TEXTS
from restaurant.services.language_admin_service import LanguageAdminService
from restaurant.services.site_settings_service import (
    InvalidSettingError,
    OrderingSettings,
    SiteSettingsService,
)

PHONE_KEY = "footer.phone_value"
ADDRESS_KEY = "footer.address_value"
HOURS_KEY = "footer.hours_value"
PAUSE_MESSAGE_KEY = "ordering.paused_message"

PHONE_MAX_LENGTH = 40
ADDRESS_MAX_LENGTH = 200
HOURS_MAX_LENGTH = 120
PAUSE_MESSAGE_MAX_LENGTH = 200
PHONE_CHARACTERS = frozenset("0123456789۰۱۲۳۴۵۶۷۸۹+-() ")


@dataclass(frozen=True)
class ContactDetails:
    """What the footer and the contact page show, per language (the phone is one value)."""

    phone: str
    address: dict[str, str]
    hours: dict[str, str]
    pause_message: dict[str, str]


@dataclass(frozen=True)
class SettingsData:
    """Everything the settings page edits."""

    ordering: OrderingSettings
    contact: ContactDetails


class SettingsAdminService:
    """Reads and saves the settings page as one unit."""

    def __init__(
        self, site_settings: SiteSettingsService, language_admin: LanguageAdminService
    ) -> None:
        """Receive the collaborators instead of importing them, so tests can swap them."""
        self._site_settings = site_settings
        self._language_admin = language_admin

    def load(self) -> SettingsData:
        """Return the current ordering settings and contact details."""
        texts = self._language_admin.get_texts(
            [PHONE_KEY, ADDRESS_KEY, HOURS_KEY, PAUSE_MESSAGE_KEY]
        )
        first_code = SUPPORTED_LANGUAGE_CODES[0]
        return SettingsData(
            ordering=self._site_settings.get_ordering_settings(),
            contact=ContactDetails(
                phone=texts[PHONE_KEY][first_code],
                address=texts[ADDRESS_KEY],
                hours=texts[HOURS_KEY],
                pause_message=texts[PAUSE_MESSAGE_KEY],
            ),
        )

    def save(self, data: SettingsData) -> None:
        """Validate and store everything. The caller commits. Raises InvalidSettingError."""
        self._check_contact(data.contact)
        self._site_settings.set_ordering_settings(data.ordering)
        entries = {
            PHONE_KEY: {code: data.contact.phone for code in SUPPORTED_LANGUAGE_CODES},
            ADDRESS_KEY: data.contact.address,
            HOURS_KEY: data.contact.hours,
            PAUSE_MESSAGE_KEY: data.contact.pause_message,
        }
        self._language_admin.save_texts(entries)

    @staticmethod
    def _check_contact(contact: ContactDetails) -> None:
        """Refuse values that are too long or a phone with odd characters."""
        phone = contact.phone.strip()
        # The built-in placeholder ("[phone]") is allowed so the untouched page can be saved.
        placeholders = set(DEFAULT_TEXTS[PHONE_KEY].values())
        if phone not in placeholders and (
            len(phone) > PHONE_MAX_LENGTH or not set(phone) <= PHONE_CHARACTERS
        ):
            raise InvalidSettingError("phone", "format")
        limits = (
            ("address", contact.address, ADDRESS_MAX_LENGTH),
            ("hours", contact.hours, HOURS_MAX_LENGTH),
            ("pause_message", contact.pause_message, PAUSE_MESSAGE_MAX_LENGTH),
        )
        for name, values, limit in limits:
            if any(len(text.strip()) > limit for text in values.values()):
                raise InvalidSettingError(name, "length")
