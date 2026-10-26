"""Queries for saved addresses, verification codes and contact-form messages."""

from sqlalchemy import delete, func, select, update

from restaurant.models import Address, ContactMessage, VerificationCode
from restaurant.repositories.base import BaseRepository


class AddressRepository(BaseRepository[Address]):
    """Reads and stores the address book of each customer."""

    model = Address

    def list_for_user(self, user_id: int) -> list[Address]:
        """Return the customer's addresses, the default one first."""
        statement = (
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(Address.is_default.desc(), Address.id)
        )
        return list(self._session.scalars(statement))

    def get_for_user(self, user_id: int, address_id: int) -> Address | None:
        """Return the address if it belongs to this customer, else None."""
        return self._session.scalar(
            select(Address).where(Address.id == address_id, Address.user_id == user_id)
        )

    def find_by_text(self, user_id: int, text: str) -> Address | None:
        """Return the customer's address with exactly this text, or None."""
        return self._session.scalar(
            select(Address).where(Address.user_id == user_id, Address.text == text)
        )

    def count_for_user(self, user_id: int) -> int:
        """Return how many addresses the customer has saved."""
        return (
            self._session.scalar(select(func.count(Address.id)).where(Address.user_id == user_id))
            or 0
        )

    def clear_default(self, user_id: int) -> None:
        """Make none of the customer's addresses the default."""
        self._session.execute(
            update(Address).where(Address.user_id == user_id).values(is_default=False)
        )

    def delete(self, address: Address) -> None:
        """Stage the removal of an address. The caller commits."""
        self._session.delete(address)


class VerificationCodeRepository(BaseRepository[VerificationCode]):
    """Reads and stores phone verification codes."""

    model = VerificationCode

    def latest_for_user(self, user_id: int) -> VerificationCode | None:
        """Return the newest code issued to this user, or None."""
        return self._session.scalar(
            select(VerificationCode)
            .where(VerificationCode.user_id == user_id)
            .order_by(VerificationCode.id.desc())
        )

    def delete_for_user(self, user_id: int) -> None:
        """Remove every code of this user (a new one replaces them, or the user is verified)."""
        self._session.execute(delete(VerificationCode).where(VerificationCode.user_id == user_id))


class ContactMessageRepository(BaseRepository[ContactMessage]):
    """Reads and stores the messages from the contact form."""

    model = ContactMessage

    def list_newest(self, offset: int, limit: int) -> list[ContactMessage]:
        """Return one page of messages, newest first."""
        statement = (
            select(ContactMessage).order_by(ContactMessage.id.desc()).offset(offset).limit(limit)
        )
        return list(self._session.scalars(statement))

    def count_unread(self) -> int:
        """Return how many messages nobody has opened yet."""
        return (
            self._session.scalar(
                select(func.count(ContactMessage.id)).where(ContactMessage.is_read.is_(False))
            )
            or 0
        )

    def delete(self, message: ContactMessage) -> None:
        """Stage the removal of a message. The caller commits."""
        self._session.delete(message)
