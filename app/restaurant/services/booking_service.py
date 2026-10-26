"""Table reservations: what is free, making a booking, confirming and cancelling it.

The overlap rule (technical plan, section 4): two bookings on one table collide when
`start_a < end_b` and `start_b < end_a`. Only confirmed bookings hold a table. Every
change that depends on that check runs under SQLite's write lock (`begin_immediate`),
so two simultaneous requests are decided one after the other.
"""

import secrets
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import StrEnum

from sqlalchemy.orm import Session

from restaurant.constants import ReservationStatus
from restaurant.models import DiningTable, Reservation
from restaurant.repositories import ReservationRepository, TableRepository
from restaurant.services.schedule_service import ScheduleService
from restaurant.services.site_settings_service import BookingRules, SiteSettingsService
from restaurant.transactions import begin_immediate

TOKEN_BYTES = 9
MAX_GUESTS_LIMIT = 50


class BookingProblem(StrEnum):
    """Why a booking was refused; each value is part of the text key `reserve.error.<value>`."""

    CLOSED = "closed"
    OUTSIDE_HOURS = "outside_hours"
    PAST = "past"
    TOO_FAR = "too_far"
    BAD_TIME = "bad_time"
    BAD_GUESTS = "bad_guests"
    NO_TABLE = "no_table"
    TABLE_TOO_SMALL = "table_too_small"
    TABLE_TAKEN = "table_taken"
    NOT_PENDING = "not_pending"
    ALREADY_CANCELLED = "already_cancelled"


class BookingError(ValueError):
    """A booking was refused; `problem` says why."""

    def __init__(self, problem: BookingProblem) -> None:
        """Keep the reason so the caller can answer in the page language."""
        super().__init__(problem.value)
        self.problem = problem


class TableState(StrEnum):
    """What a table looks like for one day, time and number of guests."""

    FREE = "free"
    BUSY = "busy"
    TOO_SMALL = "too_small"


@dataclass(frozen=True)
class TableAvailability:
    """One table with its state."""

    table: DiningTable
    state: TableState

    @property
    def is_free(self) -> bool:
        """Return True when the table can be chosen."""
        return self.state is TableState.FREE


@dataclass(frozen=True)
class SlotAvailability:
    """One start time and how many suitable tables are free at that time."""

    start: time
    free_tables: int

    @property
    def is_available(self) -> bool:
        """Return True when at least one suitable table is free."""
        return self.free_tables > 0


@dataclass(frozen=True)
class DayAvailability:
    """What a guest can choose on one day. `is_open` is False for closed or unbookable days."""

    day: date
    is_open: bool
    slots: list[SlotAvailability] = field(default_factory=list)


@dataclass(frozen=True)
class ReservationRequest:
    """Everything needed to book a table."""

    day: date
    start: time
    guests: int
    table_id: int
    customer_name: str
    customer_phone: str
    language_code: str
    note: str = ""
    user_id: int | None = None


class BookingService:
    """Checks and changes reservations. The caller commits."""

    def __init__(
        self,
        session: Session,
        table_repository: TableRepository,
        reservation_repository: ReservationRepository,
        schedule_service: ScheduleService,
        settings_service: SiteSettingsService,
    ) -> None:
        """Receive the collaborators instead of importing them, so tests can swap them."""
        self._session = session
        self._tables = table_repository
        self._reservations = reservation_repository
        self._schedule = schedule_service
        self._settings = settings_service

    # --- reading -------------------------------------------------------

    def rules(self) -> BookingRules:
        """Return the current reservation rules."""
        return self._settings.get_booking_rules()

    def max_guests(self) -> int:
        """Return the largest party a single table can seat (0 when there are no tables)."""
        capacities = [table.capacity for table in self._tables.list_ordered(only_active=True)]
        return min(max(capacities, default=0), MAX_GUESTS_LIMIT)

    def get_reservation(self, reservation_id: int) -> Reservation | None:
        """Return the reservation with this id, or None."""
        return self._reservations.get(reservation_id)

    def list_for_admin(
        self,
        *,
        day: date | None = None,
        status: ReservationStatus | None = None,
        now: datetime,
    ) -> list[Reservation]:
        """Return reservations for the admin list: one day, or everything from today onwards."""
        if day is not None:
            begin = datetime.combine(day, time.min)
            return self._reservations.list_filtered(
                status=status, from_time=begin, until_time=begin + timedelta(days=1)
            )
        return self._reservations.list_filtered(
            status=status, from_time=datetime.combine(now.date(), time.min)
        )

    def count_waiting(self, now: datetime) -> int:
        """Return how many bookings wait for an answer and have not ended yet."""
        return self._reservations.count_pending_from(now)

    def find_by_token(self, public_token: str) -> Reservation | None:
        """Return the reservation with this public token, or None."""
        return self._reservations.get_by_token(public_token)

    def list_for_user(self, user_id: int) -> list[Reservation]:
        """Return a customer's reservations, the latest day first."""
        return self._reservations.list_for_user(user_id)

    def list_tables(self) -> list[DiningTable]:
        """Return the active tables in floor-plan order."""
        return self._tables.list_ordered(only_active=True)

    def bookable_window(self, now: datetime) -> tuple[date, date]:
        """Return the first and the last day a guest may book."""
        today = now.date()
        return today, today + timedelta(days=self.rules().max_advance_days)

    def day_availability(self, day: date, guests: int, now: datetime) -> DayAvailability:
        """Return the start times of a day and how many suitable tables each still has."""
        rules = self.rules()
        if self._schedule.hours_on(day) is None or not self._in_window(day, now, rules):
            return DayAvailability(day=day, is_open=False)
        starts = self._schedule.start_times(day, rules, now)
        suitable = [t for t in self._tables.list_ordered(only_active=True) if t.capacity >= guests]
        stay = timedelta(minutes=rules.duration_minutes)
        day_start = datetime.combine(day, time.min)
        holds = self._reservations.list_overlapping(day_start, day_start + timedelta(days=2))
        slots = []
        for start in starts:
            begin = datetime.combine(day, start)
            taken = {r.table_id for r in holds if r.starts_at < begin + stay and r.ends_at > begin}
            slots.append(SlotAvailability(start, sum(1 for t in suitable if t.id not in taken)))
        return DayAvailability(day=day, is_open=True, slots=slots)

    def tables_at(
        self, day: date, start: time, guests: int, now: datetime, *, by_staff: bool = False
    ) -> list[TableAvailability]:
        """Return every active table with its state for this day, time and party size.

        Raises BookingError when the day or time cannot be booked at all.
        """
        rules = self.rules()
        begin, end = self._check_time(day, start, now, rules, by_staff=by_staff)
        self._check_guests(guests)
        taken = {r.table_id for r in self._reservations.list_overlapping(begin, end)}
        result = []
        for table in self._tables.list_ordered(only_active=True):
            if table.capacity < guests:
                state = TableState.TOO_SMALL
            elif table.id in taken:
                state = TableState.BUSY
            else:
                state = TableState.FREE
            result.append(TableAvailability(table, state))
        return result

    def alternatives_for(self, reservation: Reservation) -> list[DiningTable]:
        """Return the active tables that could take this reservation instead of its own."""
        taken = {
            r.table_id
            for r in self._reservations.list_overlapping(
                reservation.starts_at, reservation.ends_at, exclude_id=reservation.id
            )
        }
        return [
            table
            for table in self._tables.list_ordered(only_active=True)
            if table.capacity >= reservation.guests
            and table.id not in taken
            and table.id != reservation.table_id
        ]

    # --- making and changing bookings -------------------------------------

    def reserve(
        self,
        request: ReservationRequest,
        now: datetime,
        *,
        by_staff: bool = False,
        status: ReservationStatus | None = None,
    ) -> Reservation:
        """Book a table. Raises BookingError.

        A guest's booking waits for confirmation unless the rules confirm automatically;
        staff may skip the notice time, the booking window and the start-time grid, and may
        choose the status. Nothing is stored when a check fails.
        """
        rules = self.rules()
        begin, end = self._check_time(request.day, request.start, now, rules, by_staff=by_staff)
        self._check_guests(request.guests)
        begin_immediate(self._session)
        table = self._tables.get(request.table_id)
        if table is None or not table.is_active:
            raise BookingError(BookingProblem.NO_TABLE)
        if table.capacity < request.guests:
            raise BookingError(BookingProblem.TABLE_TOO_SMALL)
        if self._reservations.list_overlapping(begin, end, table_id=table.id):
            raise BookingError(BookingProblem.TABLE_TAKEN)
        final_status = status or (
            ReservationStatus.CONFIRMED if rules.auto_confirm else ReservationStatus.PENDING
        )
        reservation = Reservation(
            public_token=secrets.token_urlsafe(TOKEN_BYTES),
            user_id=request.user_id,
            table=table,
            table_label=table.label,
            language_code=request.language_code,
            customer_name=request.customer_name.strip(),
            customer_phone=request.customer_phone,
            guests=request.guests,
            starts_at=begin,
            ends_at=end,
            status=final_status,
            note=request.note.strip(),
        )
        return self._reservations.add(reservation)

    def confirm(self, reservation: Reservation) -> None:
        """Confirm a waiting booking. Raises BookingError (not pending, or the table is taken)."""
        begin_immediate(self._session)
        self._reservations.refresh(reservation)
        if reservation.status is not ReservationStatus.PENDING:
            raise BookingError(BookingProblem.NOT_PENDING)
        self._require_free_table(reservation, reservation.table_id)
        reservation.status = ReservationStatus.CONFIRMED

    def cancel(self, reservation: Reservation) -> None:
        """Cancel a booking (waiting or confirmed); its table is free again."""
        if reservation.status is ReservationStatus.CANCELLED:
            raise BookingError(BookingProblem.ALREADY_CANCELLED)
        reservation.status = ReservationStatus.CANCELLED

    def change_table(self, reservation: Reservation, table_id: int) -> None:
        """Move a booking to another table. Raises BookingError."""
        if reservation.status is ReservationStatus.CANCELLED:
            raise BookingError(BookingProblem.ALREADY_CANCELLED)
        begin_immediate(self._session)
        table = self._tables.get(table_id)
        if table is None or not table.is_active:
            raise BookingError(BookingProblem.NO_TABLE)
        if table.capacity < reservation.guests:
            raise BookingError(BookingProblem.TABLE_TOO_SMALL)
        self._require_free_table(reservation, table.id)
        reservation.table = table
        reservation.table_label = table.label

    # --- helpers -------------------------------------------------------

    def _require_free_table(self, reservation: Reservation, table_id: int | None) -> None:
        """Raise TABLE_TAKEN when a confirmed booking already holds the table at that time."""
        clashes = self._reservations.list_overlapping(
            reservation.starts_at,
            reservation.ends_at,
            table_id=table_id,
            exclude_id=reservation.id,
        )
        if table_id is None or clashes:
            raise BookingError(BookingProblem.TABLE_TAKEN)

    @staticmethod
    def _in_window(day: date, now: datetime, rules: BookingRules) -> bool:
        """Return True when the day is today or later, and not beyond the booking window."""
        today = now.date()
        return today <= day <= today + timedelta(days=rules.max_advance_days)

    def _check_time(
        self, day: date, start: time, now: datetime, rules: BookingRules, *, by_staff: bool
    ) -> tuple[datetime, datetime]:
        """Return (start, end) of the stay, or raise the BookingError that says what is wrong."""
        hours = self._schedule.hours_on(day)
        if hours is None:
            raise BookingError(BookingProblem.CLOSED)
        begin = datetime.combine(day, start)
        end = begin + timedelta(minutes=rules.duration_minutes)
        if start < hours.opens_at or end > datetime.combine(day, hours.closes_at):
            raise BookingError(BookingProblem.OUTSIDE_HOURS)
        if by_staff:
            return begin, end
        if day < now.date():
            raise BookingError(BookingProblem.PAST)
        if day > now.date() + timedelta(days=rules.max_advance_days):
            raise BookingError(BookingProblem.TOO_FAR)
        if start not in self._schedule.start_times(day, rules, now):
            earliest = now + timedelta(minutes=rules.min_notice_minutes)
            raise BookingError(BookingProblem.PAST if begin < earliest else BookingProblem.BAD_TIME)
        return begin, end

    def _check_guests(self, guests: int) -> None:
        """Raise BAD_GUESTS unless the party fits at the biggest table."""
        if not 1 <= guests <= self.max_guests():
            raise BookingError(BookingProblem.BAD_GUESTS)
