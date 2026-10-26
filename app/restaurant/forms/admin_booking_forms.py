"""Admin forms for tables, manual bookings, closing days and the reservation rules."""

import datetime
from collections.abc import Mapping

from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, TextAreaField
from wtforms.fields import SelectChoice
from wtforms.validators import ValidationError

from restaurant.booking_web import parse_day, parse_start
from restaurant.constants import ReservationStatus
from restaurant.forms.fields import WholeNumberField
from restaurant.language_context import get_translator
from restaurant.phone import normalize_mobile
from restaurant.services import BookingRules, ReservationRequest, TableInput
from restaurant.services.site_settings_service import (
    DURATION_MINUTES_RANGE,
    MAX_ADVANCE_DAYS_RANGE,
    MIN_NOTICE_MINUTES_RANGE,
    SLOT_MINUTES_RANGE,
)
from restaurant.services.table_admin_service import MAX_CAPACITY, MAX_LABEL_LENGTH

MAX_SORT_ORDER = 9999
MAX_REASON_LENGTH = 120
MAX_NAME_LENGTH = 120
MAX_NOTE_LENGTH = 300
WEEKDAY_COUNT = 7


def _in_range(field: WholeNumberField, allowed: tuple[int, int]) -> None:
    """Require a whole number inside `allowed` (both ends included)."""
    if field.data is None or not allowed[0] <= field.data <= allowed[1]:
        raise ValidationError(get_translator()("admin.reservations.error.range"))


class TableForm(FlaskForm):
    """The table form: the label shown on the floor plan, the seats and the order."""

    label = StringField()
    capacity = WholeNumberField()
    sort_order = WholeNumberField(default=0)
    is_active = BooleanField(default=True)

    def validate_label(self, field: StringField) -> None:
        """Require a short label."""
        field.data = (field.data or "").strip()
        if not field.data or len(field.data) > MAX_LABEL_LENGTH:
            raise ValidationError(get_translator()("admin.tables.error.label"))

    def validate_capacity(self, field: WholeNumberField) -> None:
        """Require 1 to 50 seats."""
        _in_range(field, (1, MAX_CAPACITY))

    def validate_sort_order(self, field: WholeNumberField) -> None:
        """Keep the order number small; an empty field means 0."""
        field.data = field.data or 0
        if not 0 <= field.data <= MAX_SORT_ORDER:
            raise ValidationError(get_translator()("admin.error.number"))

    def to_input(self) -> TableInput:
        """Return the validated values as the service's input object."""
        return TableInput(
            label=self.label.data,
            capacity=self.capacity.data,
            sort_order=self.sort_order.data,
            is_active=self.is_active.data,
        )


class ManualReservationForm(FlaskForm):
    """A booking made by staff: any table, any time inside the opening hours."""

    date = StringField()
    time = StringField()
    guests = WholeNumberField(default=2)
    table_id = SelectField(coerce=int, validate_choice=False)
    status = SelectField(
        choices=[
            SelectChoice(ReservationStatus.CONFIRMED.value, ReservationStatus.CONFIRMED.value),
            SelectChoice(ReservationStatus.PENDING.value, ReservationStatus.PENDING.value),
        ],
        default=ReservationStatus.CONFIRMED.value,
    )
    customer_name = StringField()
    customer_phone = StringField()
    note = TextAreaField()

    def set_table_choices(self, choices: list[tuple[int, str]]) -> None:
        """Fill the table list with (id, label) pairs."""
        self.table_id.choices = [SelectChoice(value, label) for value, label in choices]

    def validate_date(self, field: StringField) -> None:
        """Require a real day (it comes from the date picker)."""
        field.data = (field.data or "").strip()
        if parse_day(field.data) is None:
            raise ValidationError(get_translator()("reserve.error.pick_day"))

    def validate_time(self, field: StringField) -> None:
        """Require a time like 19:30."""
        field.data = (field.data or "").strip()
        if parse_start(field.data) is None:
            raise ValidationError(get_translator()("reserve.error.pick_time"))

    def validate_guests(self, field: WholeNumberField) -> None:
        """Require a positive number (the service checks it against the table)."""
        if field.data is None or field.data < 1:
            raise ValidationError(get_translator()("reserve.error.bad_guests"))

    def validate_table_id(self, field: SelectField) -> None:
        """Require one of the listed tables."""
        if field.data not in {choice.value for choice in field.choices}:
            raise ValidationError(get_translator()("reserve.error.pick_table"))

    def validate_customer_name(self, field: StringField) -> None:
        """Require a name."""
        field.data = (field.data or "").strip()
        if not 2 <= len(field.data) <= MAX_NAME_LENGTH:
            raise ValidationError(get_translator()("checkout.error.name"))

    def validate_customer_phone(self, field: StringField) -> None:
        """Require an Iranian mobile number and store it in its clean form."""
        number = normalize_mobile(field.data or "")
        if number is None:
            raise ValidationError(get_translator()("checkout.error.phone"))
        field.data = number

    def validate_note(self, field: TextAreaField) -> None:
        """Keep the note short."""
        field.data = (field.data or "").strip()
        if len(field.data) > MAX_NOTE_LENGTH:
            raise ValidationError(get_translator()("checkout.error.note"))

    @property
    def chosen_status(self) -> ReservationStatus:
        """The status the booking starts in."""
        return ReservationStatus(self.status.data)

    def to_request(self, language_code: str) -> ReservationRequest:
        """Return the validated values as the booking service's request."""
        return ReservationRequest(
            day=parse_day(self.date.data),
            start=parse_start(self.time.data),
            guests=self.guests.data,
            table_id=self.table_id.data,
            customer_name=self.customer_name.data,
            customer_phone=self.customer_phone.data,
            language_code=language_code,
            note=self.note.data,
        )


class ClosureForm(FlaskForm):
    """Close one day: the day comes from the date picker."""

    date = StringField()
    reason = StringField()

    def validate_date(self, field: StringField) -> None:
        """Require a real day."""
        field.data = (field.data or "").strip()
        if parse_day(field.data) is None:
            raise ValidationError(get_translator()("reserve.error.pick_day"))

    def validate_reason(self, field: StringField) -> None:
        """Keep the reason short; it may be empty."""
        field.data = (field.data or "").strip()
        if len(field.data) > MAX_REASON_LENGTH:
            raise ValidationError(get_translator()("admin.error.too_long"))

    @property
    def day(self) -> datetime.date:
        """The chosen day."""
        return parse_day(self.date.data)


class RulesForm(FlaskForm):
    """How far ahead guests can book, how long they stay and who confirms."""

    max_advance_days = WholeNumberField()
    duration_minutes = WholeNumberField()
    slot_minutes = WholeNumberField()
    min_notice_minutes = WholeNumberField()
    auto_confirm = BooleanField()

    def validate_max_advance_days(self, field: WholeNumberField) -> None:
        """Keep the value inside its allowed range."""
        _in_range(field, MAX_ADVANCE_DAYS_RANGE)

    def validate_duration_minutes(self, field: WholeNumberField) -> None:
        """Keep the value inside its allowed range."""
        _in_range(field, DURATION_MINUTES_RANGE)

    def validate_slot_minutes(self, field: WholeNumberField) -> None:
        """Keep the value inside its allowed range."""
        _in_range(field, SLOT_MINUTES_RANGE)

    def validate_min_notice_minutes(self, field: WholeNumberField) -> None:
        """Keep the value inside its allowed range."""
        _in_range(field, MIN_NOTICE_MINUTES_RANGE)

    def to_rules(self) -> BookingRules:
        """Return the validated values as booking rules."""
        return BookingRules(
            max_advance_days=self.max_advance_days.data,
            duration_minutes=self.duration_minutes.data,
            slot_minutes=self.slot_minutes.data,
            min_notice_minutes=self.min_notice_minutes.data,
            auto_confirm=self.auto_confirm.data,
        )


def read_weekly_hours(
    values: Mapping[str, str],
) -> tuple[list[tuple[int, datetime.time, datetime.time, bool]], set[int]]:
    """Read the weekly hours form: fields `opens_N`, `closes_N`, `closed_N` for weekday N (0-6).

    Returns the parsed rows and the weekdays whose times were unreadable. A closed day keeps
    whatever times were typed, or 12:00 to 23:00 when they were empty.
    """
    rows, broken = [], set()
    for weekday in range(WEEKDAY_COUNT):
        is_closed = values.get(f"closed_{weekday}") is not None
        opens = parse_start(values.get(f"opens_{weekday}", ""))
        closes = parse_start(values.get(f"closes_{weekday}", ""))
        if is_closed:
            opens = opens or datetime.time(12, 0)
            closes = closes or datetime.time(23, 0)
        if opens is None or closes is None:
            broken.add(weekday)
            continue
        rows.append((weekday, opens, closes, is_closed))
    return rows, broken
