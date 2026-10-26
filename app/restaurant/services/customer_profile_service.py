"""A signed-in customer's own data: name, e-mail, password and the address book."""

import re
from dataclasses import dataclass
from enum import StrEnum

from werkzeug.security import check_password_hash

from restaurant.constants import MIN_PASSWORD_LENGTH
from restaurant.models import Address, User
from restaurant.repositories import AddressRepository, UserRepository
from restaurant.services.auth_service import hash_password

MAX_NAME_LENGTH = 120
MIN_NAME_LENGTH = 2
MAX_ADDRESSES = 10
MAX_ADDRESS_LENGTH = 500
MAX_LABEL_LENGTH = 60
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ProfileProblem(StrEnum):
    """Why a profile or address change was refused."""

    BAD_NAME = "bad_name"
    BAD_EMAIL = "bad_email"
    EMAIL_TAKEN = "email_taken"
    WRONG_PASSWORD = "wrong_password"
    WEAK_PASSWORD = "weak_password"
    EMPTY_ADDRESS = "empty_address"
    ADDRESS_TOO_LONG = "address_too_long"
    TOO_MANY_ADDRESSES = "too_many_addresses"
    UNKNOWN_ADDRESS = "unknown_address"


class ProfileError(ValueError):
    """A change cannot be accepted; `problem` says why."""

    def __init__(self, problem: ProfileProblem) -> None:
        """Keep the problem for the page to turn into a message."""
        super().__init__(problem.value)
        self.problem = problem


@dataclass(frozen=True)
class AddressInput:
    """What the customer typed for one address."""

    label: str
    text: str
    is_default: bool = False


class CustomerProfileService:
    """Changes a customer's own profile and address book. Callers commit."""

    def __init__(self, user_repository: UserRepository, address_repository: AddressRepository):
        """Receive the repositories instead of importing them, so tests can swap them."""
        self._users = user_repository
        self._addresses = address_repository

    def update_profile(self, user: User, name: str, email: str) -> None:
        """Change the display name and the optional e-mail address."""
        name = name.strip()
        email = email.strip().lower()
        if not MIN_NAME_LENGTH <= len(name) <= MAX_NAME_LENGTH:
            raise ProfileError(ProfileProblem.BAD_NAME)
        if email and not _EMAIL_PATTERN.match(email):
            raise ProfileError(ProfileProblem.BAD_EMAIL)
        other = self._users.get_by_email(email) if email else None
        if other is not None and other.id != user.id:
            raise ProfileError(ProfileProblem.EMAIL_TAKEN)
        user.display_name = name
        user.email = email or None

    def change_password(self, user: User, current: str, new: str) -> None:
        """Set a new password after the current one is confirmed."""
        if not user.password_hash or not check_password_hash(user.password_hash, current):
            raise ProfileError(ProfileProblem.WRONG_PASSWORD)
        if len(new) < MIN_PASSWORD_LENGTH:
            raise ProfileError(ProfileProblem.WEAK_PASSWORD)
        user.password_hash = hash_password(new)

    def list_addresses(self, user: User) -> list[Address]:
        """Return the customer's addresses, the default first."""
        return self._addresses.list_for_user(user.id)

    def add_address(self, user: User, data: AddressInput) -> Address:
        """Save a new address. The first one is always the default."""
        label, text = self._clean(data)
        if self._addresses.count_for_user(user.id) >= MAX_ADDRESSES:
            raise ProfileError(ProfileProblem.TOO_MANY_ADDRESSES)
        make_default = data.is_default or self._addresses.count_for_user(user.id) == 0
        if make_default:
            self._addresses.clear_default(user.id)
        return self._addresses.add(
            Address(user_id=user.id, label=label, text=text, is_default=make_default)
        )

    def update_address(self, user: User, address_id: int, data: AddressInput) -> Address:
        """Change an address of this customer."""
        address = self._own_address(user, address_id)
        address.label, address.text = self._clean(data)
        if data.is_default:
            self._make_default(user, address)
        return address

    def delete_address(self, user: User, address_id: int) -> None:
        """Remove an address; when it was the default, the oldest remaining one takes over."""
        address = self._own_address(user, address_id)
        was_default = address.is_default
        self._addresses.delete(address)
        self._addresses.flush()
        if was_default:
            remaining = self._addresses.list_for_user(user.id)
            if remaining:
                remaining[0].is_default = True

    def set_default_address(self, user: User, address_id: int) -> None:
        """Make one of the customer's addresses the default."""
        self._make_default(user, self._own_address(user, address_id))

    def remember_address(self, user: User, text: str) -> bool:
        """Save the address typed at checkout unless it is already saved.

        Returns True when a new address was stored. A full or invalid book is left alone.
        """
        text = " ".join(text.split())
        if not text or len(text) > MAX_ADDRESS_LENGTH:
            return False
        if self._addresses.find_by_text(user.id, text) is not None:
            return False
        if self._addresses.count_for_user(user.id) >= MAX_ADDRESSES:
            return False
        self.add_address(user, AddressInput(label="", text=text))
        return True

    def _make_default(self, user: User, address: Address) -> None:
        """Mark one address as the default and clear the others."""
        self._addresses.clear_default(user.id)
        address.is_default = True

    def _own_address(self, user: User, address_id: int) -> Address:
        """Return the address if it is this customer's, else refuse (no hints about others)."""
        address = self._addresses.get_for_user(user.id, address_id)
        if address is None:
            raise ProfileError(ProfileProblem.UNKNOWN_ADDRESS)
        return address

    @staticmethod
    def _clean(data: AddressInput) -> tuple[str, str]:
        """Return the trimmed label and text, refusing an empty or too long address."""
        text = " ".join(data.text.split())
        label = data.label.strip()[:MAX_LABEL_LENGTH]
        if not text:
            raise ProfileError(ProfileProblem.EMPTY_ADDRESS)
        if len(text) > MAX_ADDRESS_LENGTH:
            raise ProfileError(ProfileProblem.ADDRESS_TOO_LONG)
        return label, text
