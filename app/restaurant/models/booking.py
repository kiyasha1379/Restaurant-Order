"""Table booking: the tables of the hall, reservations, opening hours and closing days.

Times are naive `Asia/Tehran` values (technical plan, section 4). A reservation keeps the
table's label as a copy, so deleting or renaming a table never rewrites what a guest booked.
"""

from datetime import date, datetime, time

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from restaurant.constants import ReservationStatus
from restaurant.extensions import db
from restaurant.models.access import User
from restaurant.models.columns import enum_type
from restaurant.models.mixins import TimestampMixin


class DiningTable(db.Model):
    """One table on the floor plan. The hall draws tables in `sort_order`."""

    __tablename__ = "dining_tables"
    __table_args__ = (CheckConstraint("capacity >= 1", name="capacity_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(20), unique=True)
    capacity: Mapped[int]
    sort_order: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)

    reservations: Mapped[list["Reservation"]] = relationship(back_populates="table")


class Reservation(TimestampMixin, db.Model):
    """One booking of a table. `public_token` is the unguessable part of the booking address."""

    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ends_after_start"),
        CheckConstraint("guests >= 1", name="guests_positive"),
        Index("ix_reservations_table_start", "table_id", "starts_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_token: Mapped[str] = mapped_column(String(32), unique=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    table_id: Mapped[int | None] = mapped_column(
        ForeignKey("dining_tables.id", ondelete="SET NULL")
    )
    table_label: Mapped[str] = mapped_column(String(20))
    language_code: Mapped[str] = mapped_column(String(5))
    customer_name: Mapped[str] = mapped_column(String(120))
    customer_phone: Mapped[str] = mapped_column(String(20))
    guests: Mapped[int]
    starts_at: Mapped[datetime] = mapped_column(index=True)
    ends_at: Mapped[datetime]
    status: Mapped[ReservationStatus] = mapped_column(
        enum_type(ReservationStatus), default=ReservationStatus.PENDING
    )
    note: Mapped[str] = mapped_column(Text, default="")

    table: Mapped[DiningTable | None] = relationship(back_populates="reservations")
    user: Mapped[User | None] = relationship()

    @property
    def number(self) -> int:
        """The booking number shown to people (the row id)."""
        return self.id

    @property
    def holds_table(self) -> bool:
        """Return True when this booking keeps its table away from others (confirmed only)."""
        return self.status is ReservationStatus.CONFIRMED


class OpeningHour(db.Model):
    """When the restaurant takes guests on one weekday (`weekday` follows `date.weekday()`)."""

    __tablename__ = "opening_hours"
    __table_args__ = (CheckConstraint("weekday >= 0 AND weekday <= 6", name="weekday_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    weekday: Mapped[int] = mapped_column(unique=True)
    opens_at: Mapped[time]
    closes_at: Mapped[time]
    is_closed: Mapped[bool] = mapped_column(default=False)


class SpecialClosure(db.Model):
    """A whole day the restaurant does not take reservations (a holiday, a private event)."""

    __tablename__ = "special_closures"

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(unique=True)
    reason: Mapped[str] = mapped_column(String(160), default="")
