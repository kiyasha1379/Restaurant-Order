"""Customer accounts: saved addresses, phone verification codes and contact-form messages."""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from restaurant.extensions import db
from restaurant.models.access import User
from restaurant.models.mixins import TimestampMixin
from restaurant.timeutils import now_tehran


class Address(TimestampMixin, db.Model):
    """One delivery address in a customer's address book."""

    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(60), default="")
    text: Mapped[str] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(default=False)

    user: Mapped[User] = relationship(back_populates="addresses")


class VerificationCode(db.Model):
    """The code sent to a phone to finish a registration. Only a hash of it is stored."""

    __tablename__ = "verification_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime]
    attempts: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=now_tehran)


class ContactMessage(db.Model):
    """A message sent from the public contact form, read in the admin panel."""

    __tablename__ = "contact_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(120))
    contact: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    language_code: Mapped[str] = mapped_column(String(5))
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=now_tehran, index=True)
