"""The reservation form: day, time, guests, table and who is booking."""

import datetime

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import ValidationError

from restaurant.booking_web import parse_day, parse_start
from restaurant.forms.fields import WholeNumberField
from restaurant.language_context import get_translator
from restaurant.phone import normalize_mobile
from restaurant.services import ReservationRequest

MIN_NAME_LENGTH = 2
MAX_NAME_LENGTH = 120
MAX_NOTE_LENGTH = 300


class ReserveForm(FlaskForm):
    """Reservation details; error messages follow the page language."""

    date = StringField()
    time = StringField()
    guests = WholeNumberField(default=2)
    table_id = WholeNumberField()
    customer_name = StringField()
    customer_phone = StringField()
    note = TextAreaField()

    def validate_date(self, field: StringField) -> None:
        """Require a real day."""
        field.data = (field.data or "").strip()
        if not field.data:
            raise ValidationError(get_translator()("reserve.error.pick_day"))
        if parse_day(field.data) is None:
            raise ValidationError(get_translator()("reserve.error.bad_date"))

    def validate_time(self, field: StringField) -> None:
        """Require a start time like 19:30."""
        field.data = (field.data or "").strip()
        if not field.data:
            raise ValidationError(get_translator()("reserve.error.pick_time"))
        if parse_start(field.data) is None:
            raise ValidationError(get_translator()("reserve.error.bad_time"))

    def validate_guests(self, field: WholeNumberField) -> None:
        """Require a positive number (the service checks it against the tables)."""
        if field.data is None or field.data < 1:
            raise ValidationError(get_translator()("reserve.error.bad_guests"))

    def validate_table_id(self, field: WholeNumberField) -> None:
        """Require a chosen table."""
        if field.data is None:
            raise ValidationError(get_translator()("reserve.error.pick_table"))

    def validate_customer_name(self, field: StringField) -> None:
        """Require a name of a sensible length."""
        field.data = (field.data or "").strip()
        if not MIN_NAME_LENGTH <= len(field.data) <= MAX_NAME_LENGTH:
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
    def chosen_day(self) -> datetime.date | None:
        """The chosen day, or None when the field is empty or broken."""
        return parse_day(self.date.data or "")

    @property
    def chosen_start(self) -> datetime.time | None:
        """The chosen start time, or None when the field is empty or broken."""
        return parse_start(self.time.data or "")

    def to_request(self, language_code: str, user_id: int | None = None) -> ReservationRequest:
        """Return the validated values as the booking service's request."""
        return ReservationRequest(
            day=self.chosen_day,
            start=self.chosen_start,
            guests=self.guests.data,
            table_id=self.table_id.data,
            customer_name=self.customer_name.data,
            customer_phone=self.customer_phone.data,
            language_code=language_code,
            note=self.note.data,
            user_id=user_id,
        )
