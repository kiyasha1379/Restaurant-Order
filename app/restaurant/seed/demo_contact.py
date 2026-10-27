"""Realistic contact details for the demo footer. Safe to run twice."""

from dataclasses import replace

from restaurant.constants import LANGUAGE_CODE_ENGLISH as EN
from restaurant.constants import LANGUAGE_CODE_PERSIAN as FA
from restaurant.default_texts import DEFAULT_TEXTS
from restaurant.services import SettingsAdminService
from restaurant.services.settings_admin_service import PHONE_KEY

DEMO_PHONE = "021-12345678"
DEMO_ADDRESS = {FA: "تهران، خیابان ولیعصر، پلاک ۱۲۰", EN: "120 Valiasr Street, Tehran"}
DEMO_HOURS = {FA: "هر روز ۱۲ تا ۲۳", EN: "Daily 12:00 to 23:00"}


class DemoContactSeeder:
    """Replaces the "[phone]" style placeholders with sample details; edits are never touched."""

    def __init__(self, settings_admin: SettingsAdminService) -> None:
        """Receive the service instead of importing it, so tests can swap it."""
        self._settings_admin = settings_admin

    def seed(self) -> int:
        """Fill the contact details that still show their placeholder; return how many."""
        data = self._settings_admin.load()
        contact = data.contact
        changed = 0
        phone, address, hours = contact.phone, dict(contact.address), dict(contact.hours)
        if phone in set(DEFAULT_TEXTS[PHONE_KEY].values()):
            phone, changed = DEMO_PHONE, changed + 1
        if address == {code: DEFAULT_TEXTS["footer.address_value"][code] for code in (FA, EN)}:
            address, changed = DEMO_ADDRESS, changed + 1
        if hours == {code: DEFAULT_TEXTS["footer.hours_value"][code] for code in (FA, EN)}:
            hours, changed = DEMO_HOURS, changed + 1
        if changed:
            new_contact = replace(contact, phone=phone, address=address, hours=hours)
            self._settings_admin.save(replace(data, contact=new_contact))
        return changed
