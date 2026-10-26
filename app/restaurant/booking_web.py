"""Booking helpers shared by the reservation page and the availability API."""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any

from restaurant.formatting import format_time
from restaurant.services import BookingError, BookingService, DayAvailability, TableAvailability

TIME_FORMAT = "%H:%M"
SEARCH_DAYS = 14


def parse_day(text: str) -> date | None:
    """Parse an ISO date (2026-10-27); return None when it is not one."""
    try:
        return date.fromisoformat((text or "").strip())
    except ValueError:
        return None


def parse_start(text: str) -> time | None:
    """Parse a start time like 19:30; return None when it is not one."""
    try:
        return datetime.strptime((text or "").strip(), TIME_FORMAT).time()
    except ValueError:
        return None


def first_bookable_day(service: BookingService, guests: int, now: datetime) -> date:
    """Return the first day (from today) that still has a free start time.

    Falls back to today when nothing is free in the next two weeks.
    """
    today, last = service.bookable_window(now)
    for offset in range(SEARCH_DAYS):
        day = today + timedelta(days=offset)
        if day > last:
            break
        if any(slot.is_available for slot in service.day_availability(day, guests, now).slots):
            return day
    return today


@dataclass(frozen=True)
class BookingChoice:
    """What the visitor has chosen so far on the reservation page."""

    day: date
    guests: int
    start: time | None = None
    table_id: int | None = None


@dataclass
class FloorState:
    """The tables with their state for the chosen day and time, plus why a time was refused."""

    tables: list[TableAvailability] = field(default_factory=list)
    problem: str = ""


def describe_slots(availability: DayAvailability, language_code: str) -> list[dict[str, Any]]:
    """Return the day's start times as JSON-ready dictionaries."""
    return [
        {
            "time": slot.start.strftime(TIME_FORMAT),
            "label": format_time(slot.start, language_code),
            "free": slot.free_tables,
            "available": slot.is_available,
        }
        for slot in availability.slots
    ]


def read_floor(service: BookingService, choice: BookingChoice, now: datetime) -> FloorState:
    """Return every active table with its state; without a start time all tables are `idle`."""
    if choice.start is None:
        return FloorState()
    try:
        return FloorState(tables=service.tables_at(choice.day, choice.start, choice.guests, now))
    except BookingError as error:
        return FloorState(problem=error.problem.value)


def availability_payload(
    service: BookingService, choice: BookingChoice, now: datetime, language_code: str
) -> dict[str, Any]:
    """Return the JSON answer of `GET /api/availability`."""
    availability = service.day_availability(choice.day, choice.guests, now)
    floor = read_floor(service, choice, now)
    return {
        "date": choice.day.isoformat(),
        "open": availability.is_open,
        "guests": choice.guests,
        "max_guests": service.max_guests(),
        "slots": describe_slots(availability, language_code),
        "tables": [{"id": entry.table.id, "state": entry.state.value} for entry in floor.tables],
        "time_problem": floor.problem,
    }
