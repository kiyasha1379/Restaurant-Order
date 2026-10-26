"""Queries for tables, reservations, opening hours and closing days."""

from datetime import date, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from restaurant.constants import ReservationStatus
from restaurant.models import DiningTable, OpeningHour, Reservation, SpecialClosure
from restaurant.repositories.base import BaseRepository


class TableRepository(BaseRepository[DiningTable]):
    """Reads and removes the tables of the hall."""

    model = DiningTable

    def list_ordered(self, *, only_active: bool = False) -> list[DiningTable]:
        """Return the tables in floor-plan order."""
        statement = select(DiningTable).order_by(DiningTable.sort_order, DiningTable.id)
        if only_active:
            statement = statement.where(DiningTable.is_active.is_(True))
        return list(self._session.scalars(statement))

    def get_by_label(self, label: str) -> DiningTable | None:
        """Return the table with this label, or None."""
        return self._session.scalar(select(DiningTable).where(DiningTable.label == label))

    def delete(self, table: DiningTable) -> None:
        """Stage the removal of a table. The caller commits."""
        self._session.delete(table)


class ReservationRepository(BaseRepository[Reservation]):
    """Reads and writes reservations."""

    model = Reservation

    def get_by_token(self, public_token: str) -> Reservation | None:
        """Return the reservation behind this public token, or None."""
        return self._session.scalar(
            select(Reservation).where(Reservation.public_token == public_token)
        )

    def list_for_user(self, user_id: int) -> list[Reservation]:
        """Return a customer's reservations, the latest day first."""
        statement = (
            select(Reservation)
            .where(Reservation.user_id == user_id)
            .order_by(Reservation.starts_at.desc(), Reservation.id.desc())
        )
        return list(self._session.scalars(statement))

    def count_by_users(self, user_ids: list[int]) -> dict[int, int]:
        """Return how many reservations each of these customers has made."""
        if not user_ids:
            return {}
        rows = self._session.execute(
            select(Reservation.user_id, func.count(Reservation.id))
            .where(Reservation.user_id.in_(user_ids))
            .group_by(Reservation.user_id)
        )
        return dict(rows.all())

    def claim_guest_reservations(self, phone: str, user_id: int) -> int:
        """Attach the guest reservations made with this phone number to the customer."""
        result = self._session.execute(
            update(Reservation)
            .where(Reservation.customer_phone == phone, Reservation.user_id.is_(None))
            .values(user_id=user_id)
        )
        return result.rowcount or 0

    def list_overlapping(
        self,
        starts_at: datetime,
        ends_at: datetime,
        statuses: tuple[ReservationStatus, ...] = (ReservationStatus.CONFIRMED,),
        *,
        table_id: int | None = None,
        exclude_id: int | None = None,
    ) -> list[Reservation]:
        """Return reservations in these statuses that collide with [starts_at, ends_at).

        Two bookings collide when `start_a < end_b` and `start_b < end_a`.
        """
        statement = select(Reservation).where(
            Reservation.status.in_(statuses),
            Reservation.starts_at < ends_at,
            Reservation.ends_at > starts_at,
        )
        if table_id is not None:
            statement = statement.where(Reservation.table_id == table_id)
        if exclude_id is not None:
            statement = statement.where(Reservation.id != exclude_id)
        return list(self._session.scalars(statement))

    def list_for_day(self, day: date) -> list[Reservation]:
        """Return the reservations that start on this day, earliest first."""
        start = datetime.combine(day, datetime.min.time())
        statement = (
            select(Reservation)
            .where(
                Reservation.starts_at >= start, Reservation.starts_at < start + timedelta(days=1)
            )
            .order_by(Reservation.starts_at, Reservation.id)
        )
        return list(self._session.scalars(statement))

    def list_filtered(
        self,
        *,
        status: ReservationStatus | None = None,
        from_time: datetime | None = None,
        until_time: datetime | None = None,
        limit: int = 200,
    ) -> list[Reservation]:
        """Return reservations for the admin list, earliest first."""
        statement = select(Reservation).options(selectinload(Reservation.table))
        if status is not None:
            statement = statement.where(Reservation.status == status)
        if from_time is not None:
            statement = statement.where(Reservation.starts_at >= from_time)
        if until_time is not None:
            statement = statement.where(Reservation.starts_at < until_time)
        statement = statement.order_by(Reservation.starts_at, Reservation.id).limit(limit)
        return list(self._session.scalars(statement))

    def count_pending_from(self, from_time: datetime) -> int:
        """Return how many reservations still wait for an answer and have not started yet."""
        statement = select(Reservation.id).where(
            Reservation.status == ReservationStatus.PENDING, Reservation.ends_at > from_time
        )
        return len(list(self._session.scalars(statement)))

    def list_for_table_from(self, table_id: int, from_time: datetime) -> list[Reservation]:
        """Return upcoming reservations of a table that are still alive (not cancelled)."""
        statement = select(Reservation).where(
            Reservation.table_id == table_id,
            Reservation.ends_at > from_time,
            Reservation.status != ReservationStatus.CANCELLED,
        )
        return list(self._session.scalars(statement))


class ScheduleRepository:
    """Reads and writes opening hours and closing days (two small tables, one repository)."""

    def __init__(self, session) -> None:  # noqa: ANN001 - a SQLAlchemy session
        """Keep the session this repository works with."""
        self._session = session

    def list_hours(self) -> list[OpeningHour]:
        """Return the opening hours of every weekday that has a row."""
        return list(self._session.scalars(select(OpeningHour).order_by(OpeningHour.weekday)))

    def get_hours(self, weekday: int) -> OpeningHour | None:
        """Return the opening hours of one weekday, or None."""
        return self._session.scalar(select(OpeningHour).where(OpeningHour.weekday == weekday))

    def add_hours(self, hours: OpeningHour) -> OpeningHour:
        """Stage a new opening-hours row."""
        self._session.add(hours)
        return hours

    def list_closures(self, from_day: date | None = None) -> list[SpecialClosure]:
        """Return the closing days (from a day on, when given), earliest first."""
        statement = select(SpecialClosure).order_by(SpecialClosure.day)
        if from_day is not None:
            statement = statement.where(SpecialClosure.day >= from_day)
        return list(self._session.scalars(statement))

    def get_closure(self, day: date) -> SpecialClosure | None:
        """Return the closure on this day, or None."""
        return self._session.scalar(select(SpecialClosure).where(SpecialClosure.day == day))

    def get_closure_by_id(self, closure_id: int) -> SpecialClosure | None:
        """Return the closure with this id, or None."""
        return self._session.get(SpecialClosure, closure_id)

    def add_closure(self, closure: SpecialClosure) -> SpecialClosure:
        """Stage a new closing day."""
        self._session.add(closure)
        return closure

    def delete_closure(self, closure: SpecialClosure) -> None:
        """Stage the removal of a closing day."""
        self._session.delete(closure)
