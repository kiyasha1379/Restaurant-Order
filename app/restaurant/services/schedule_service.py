"""When the restaurant takes guests: weekly opening hours, closing days and start times."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from restaurant.constants import DEFAULT_CLOSING_TIME, DEFAULT_OPENING_TIME
from restaurant.models import OpeningHour, SpecialClosure
from restaurant.repositories import ScheduleRepository
from restaurant.services.site_settings_service import BookingRules


class ScheduleError(ValueError):
    """A change to the opening hours or closing days was refused."""


class InvalidHoursError(ScheduleError):
    """The restaurant must close later than it opens (a day may not cross midnight)."""


class DuplicateClosureError(ScheduleError):
    """The day is already a closing day."""


def _default_time(text: str) -> time:
    """Turn 'HH:MM' into a time."""
    hour, minute = text.split(":")
    return time(int(hour), int(minute))


@dataclass(frozen=True)
class DayHours:
    """The hours of one open day."""

    opens_at: time
    closes_at: time


class ScheduleService:
    """Answers 'is the restaurant open on this day, and which start times are there?'."""

    def __init__(self, schedule_repository: ScheduleRepository) -> None:
        """Receive the repository instead of importing it, so tests can swap it."""
        self._schedule = schedule_repository

    # --- reading -------------------------------------------------------

    def closure_on(self, day: date) -> SpecialClosure | None:
        """Return the closing day entry for this date, or None."""
        return self._schedule.get_closure(day)

    def hours_on(self, day: date) -> DayHours | None:
        """Return the opening hours of this date, or None when the restaurant is closed."""
        if self._schedule.get_closure(day) is not None:
            return None
        row = self._schedule.get_hours(day.weekday())
        if row is None:
            return DayHours(
                _default_time(DEFAULT_OPENING_TIME), _default_time(DEFAULT_CLOSING_TIME)
            )
        if row.is_closed:
            return None
        return DayHours(row.opens_at, row.closes_at)

    def list_hours(self) -> dict[int, OpeningHour]:
        """Return the stored opening hours keyed by weekday (`date.weekday()` numbers)."""
        return {row.weekday: row for row in self._schedule.list_hours()}

    def list_closures(self, from_day: date | None = None) -> list[SpecialClosure]:
        """Return the closing days, earliest first."""
        return self._schedule.list_closures(from_day)

    def closed_days_between(self, first: date, last: date) -> list[date]:
        """Return the days in [first, last] on which the restaurant is closed."""
        closed = []
        day = first
        while day <= last:
            if self.hours_on(day) is None:
                closed.append(day)
            day += timedelta(days=1)
        return closed

    def start_times(self, day: date, rules: BookingRules, now: datetime) -> list[time]:
        """Return the start times a guest may choose on this day.

        A time is offered when the whole stay ends before closing and, for today, when it is
        far enough ahead (the minimum notice). Times follow the slot step from opening time.
        """
        hours = self.hours_on(day)
        if hours is None:
            return []
        step = timedelta(minutes=rules.slot_minutes)
        stay = timedelta(minutes=rules.duration_minutes)
        earliest = now + timedelta(minutes=rules.min_notice_minutes)
        closing = datetime.combine(day, hours.closes_at)
        moment = datetime.combine(day, hours.opens_at)
        times = []
        while moment + stay <= closing:
            if moment >= earliest:
                times.append(moment.time())
            moment += step
        return times

    # --- changing ------------------------------------------------------

    def set_hours(self, weekday: int, opens_at: time, closes_at: time, is_closed: bool) -> None:
        """Set the opening hours of one weekday. Raises InvalidHoursError. The caller commits."""
        if not is_closed and closes_at <= opens_at:
            raise InvalidHoursError(f"{opens_at} - {closes_at}")
        row = self._schedule.get_hours(weekday)
        if row is None:
            row = self._schedule.add_hours(OpeningHour(weekday=weekday))
        row.opens_at, row.closes_at, row.is_closed = opens_at, closes_at, is_closed

    def add_closure(self, day: date, reason: str) -> SpecialClosure:
        """Close a whole day. Raises DuplicateClosureError. The caller commits."""
        if self._schedule.get_closure(day) is not None:
            raise DuplicateClosureError(day.isoformat())
        return self._schedule.add_closure(SpecialClosure(day=day, reason=reason.strip()))

    def remove_closure(self, closure_id: int) -> None:
        """Open a closed day again. Unknown ids are ignored. The caller commits."""
        closure = self._schedule.get_closure_by_id(closure_id)
        if closure is not None:
            self._schedule.delete_closure(closure)
