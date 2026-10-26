"""A sample customer account, address and contact messages for the demo. Safe to run twice."""

from restaurant.constants import LANGUAGE_CODE_ENGLISH, LANGUAGE_CODE_PERSIAN
from restaurant.models import Address, ContactMessage, User
from restaurant.repositories import AddressRepository, ContactMessageRepository, UserRepository
from restaurant.seed.demo_staff import DEMO_STAFF_PASSWORD
from restaurant.services.auth_service import hash_password

# Public on purpose: this account exists only in the demo (never in a real installation).
DEMO_CUSTOMER_EMAIL = "customer@example.com"
DEMO_CUSTOMER_PHONE = "09120000000"
DEMO_CUSTOMER_NAME = "Demo Customer"
DEMO_ADDRESS = "تهران، خیابان ولیعصر، بالاتر از میدان ونک، پلاک ۱۲، واحد ۳"
DEMO_MESSAGES = (
    (
        "سارا احمدی",
        "09121111111",
        "سلام، آیا پیتزای بدون گلوتن هم دارید؟ ممنون می‌شوم پاسخ بدهید.",
        LANGUAGE_CODE_PERSIAN,
    ),
    (
        "John Miller",
        "john@example.com",
        "Hello! Do you take bookings for a group of 12 on Friday evening?",
        LANGUAGE_CODE_ENGLISH,
    ),
)


class DemoCustomerSeeder:
    """Adds the sample customer and two contact messages when they are missing."""

    def __init__(
        self,
        user_repository: UserRepository,
        address_repository: AddressRepository,
        message_repository: ContactMessageRepository,
    ) -> None:
        """Receive the repositories instead of importing them, so tests can swap them."""
        self._users = user_repository
        self._addresses = address_repository
        self._messages = message_repository

    def seed(self) -> int:
        """Add what is missing and return how many rows were added."""
        added = 0
        if self._users.get_by_email(DEMO_CUSTOMER_EMAIL) is None:
            user = self._users.add(
                User(
                    email=DEMO_CUSTOMER_EMAIL,
                    phone=DEMO_CUSTOMER_PHONE,
                    display_name=DEMO_CUSTOMER_NAME,
                    password_hash=hash_password(DEMO_STAFF_PASSWORD),
                )
            )
            self._users.flush()
            self._addresses.add(
                Address(user_id=user.id, label="خانه", text=DEMO_ADDRESS, is_default=True)
            )
            added += 2
        if self._messages.count() == 0:
            for name, contact, body, language_code in DEMO_MESSAGES:
                self._messages.add(
                    ContactMessage(
                        name=name, contact=contact, body=body, language_code=language_code
                    )
                )
                added += 1
        return added
