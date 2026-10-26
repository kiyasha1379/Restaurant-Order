"""The contact form: visitors write, staff read in the admin panel."""

from enum import StrEnum

from restaurant.models import ContactMessage
from restaurant.repositories import ContactMessageRepository

MAX_NAME_LENGTH = 120
MAX_CONTACT_LENGTH = 255
MIN_BODY_LENGTH = 5
MAX_BODY_LENGTH = 2000


class ContactProblem(StrEnum):
    """Why a message was refused."""

    BAD_NAME = "bad_name"
    BAD_CONTACT = "bad_contact"
    BAD_BODY = "bad_body"


class ContactError(ValueError):
    """A message cannot be accepted; `problem` says why."""

    def __init__(self, problem: ContactProblem) -> None:
        """Keep the problem for the page to turn into a message."""
        super().__init__(problem.value)
        self.problem = problem


class ContactService:
    """Stores and lists contact-form messages. Callers commit."""

    def __init__(self, repository: ContactMessageRepository) -> None:
        """Receive the repository instead of importing it, so tests can swap it."""
        self._repository = repository

    def submit(
        self, name: str, contact: str, body: str, language_code: str, user_id: int | None
    ) -> ContactMessage:
        """Store a new message from a visitor."""
        name, contact, body = name.strip(), contact.strip(), body.strip()
        if not 2 <= len(name) <= MAX_NAME_LENGTH:
            raise ContactError(ContactProblem.BAD_NAME)
        if not 3 <= len(contact) <= MAX_CONTACT_LENGTH:
            raise ContactError(ContactProblem.BAD_CONTACT)
        if not MIN_BODY_LENGTH <= len(body) <= MAX_BODY_LENGTH:
            raise ContactError(ContactProblem.BAD_BODY)
        message = ContactMessage(
            user_id=user_id, name=name, contact=contact, body=body, language_code=language_code
        )
        return self._repository.add(message)

    def list_messages(self, offset: int, limit: int) -> tuple[list[ContactMessage], int]:
        """Return one page of messages (newest first) and how many there are in all."""
        return self._repository.list_newest(offset, limit), self._repository.count()

    def count_unread(self) -> int:
        """Return how many messages have not been opened."""
        return self._repository.count_unread()

    def set_read(self, message_id: int, is_read: bool) -> bool:
        """Mark a message read or unread. Returns False when it does not exist."""
        message = self._repository.get(message_id)
        if message is None:
            return False
        message.is_read = is_read
        return True

    def delete(self, message_id: int) -> bool:
        """Remove a message. Returns False when it does not exist."""
        message = self._repository.get(message_id)
        if message is None:
            return False
        self._repository.delete(message)
        return True
