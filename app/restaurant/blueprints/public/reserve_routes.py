"""Public table reservation: the booking page, the confirmation page and cancelling."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from flask import abort, redirect, render_template, request, url_for
from flask_login import current_user
from werkzeug.wrappers import Response

from restaurant.blueprints.public import public_blueprint
from restaurant.booking_web import (
    BookingChoice,
    describe_slots,
    first_bookable_day,
    parse_day,
    parse_start,
    read_floor,
)
from restaurant.extensions import db
from restaurant.forms.reserve_form import ReserveForm
from restaurant.language_context import get_active_language, get_translator
from restaurant.service_factory import make_booking_service, make_schedule_service
from restaurant.services import BookingError, BookingService, TableState
from restaurant.timeutils import now_tehran

QUICK_DAY_COUNT = 3
DEFAULT_GUESTS = 2
QUICK_DAY_KEYS = ("reserve.today", "reserve.tomorrow", "reserve.after_tomorrow")


@dataclass(frozen=True)
class QuickDay:
    """One of the day buttons above the calendar."""

    day: date
    label_key: str
    is_bookable: bool


def _read_guests(text: str | None, limit: int) -> int:
    """Return the guest count from a query value, kept between 1 and the biggest table."""
    try:
        guests = int(text or DEFAULT_GUESTS)
    except ValueError:
        guests = DEFAULT_GUESTS
    return max(1, min(guests, max(limit, 1)))


def _choice_from_query(service: BookingService, now: datetime) -> BookingChoice:
    """Read the chosen day, guests, time and table from the address (the first visit)."""
    guests = _read_guests(request.args.get("guests"), service.max_guests())
    day = parse_day(request.args.get("date", ""))
    first, last = service.bookable_window(now)
    if day is None or not first <= day <= last:
        day = first_bookable_day(service, guests, now)
    table = request.args.get("table", "")
    return BookingChoice(
        day=day,
        guests=guests,
        start=parse_start(request.args.get("time", "")),
        table_id=int(table) if table.isdecimal() else None,
    )


def _choice_from_form(form: ReserveForm, service: BookingService, now: datetime) -> BookingChoice:
    """Read the chosen values from a submitted form, falling back to sensible ones."""
    guests = _read_guests(str(form.guests.data or ""), service.max_guests())
    return BookingChoice(
        day=form.chosen_day or first_bookable_day(service, guests, now),
        guests=guests,
        start=form.chosen_start,
        table_id=form.table_id.data,
    )


def _quick_days(service: BookingService, now: datetime) -> list[QuickDay]:
    """Return today, tomorrow and the day after, with whether each can be booked."""
    first, last = service.bookable_window(now)
    schedule = make_schedule_service()
    days = []
    for offset, label_key in enumerate(QUICK_DAY_KEYS[:QUICK_DAY_COUNT]):
        day = first + timedelta(days=offset)
        is_bookable = day <= last and schedule.hours_on(day) is not None
        days.append(QuickDay(day, label_key, is_bookable))
    return days


def _render_page(
    form: ReserveForm,
    choice: BookingChoice,
    service: BookingService,
    now: datetime,
    error: str = "",
) -> str:
    """Render the booking page for the current choice."""
    language = get_active_language()
    availability = service.day_availability(choice.day, choice.guests, now)
    floor = read_floor(service, choice, now)
    states = {entry.table.id: entry.state for entry in floor.tables}
    first, last = service.bookable_window(now)
    table_id = choice.table_id if states.get(choice.table_id) is TableState.FREE else None
    start = choice.start if choice.start and not floor.problem else None
    return render_template(
        "reserve.html",
        form=form,
        error=error,
        choice=choice,
        start=start,
        table_id=table_id,
        tables=service.list_tables(),
        states=states,
        slots=describe_slots(availability, language.code),
        is_open=availability.is_open,
        max_guests=service.max_guests(),
        window_first=first,
        window_last=last,
        closed_days=make_schedule_service().closed_days_between(first, last),
        quick_days=_quick_days(service, now),
    )


@public_blueprint.route("/reserve", methods=["GET", "POST"])
def reserve() -> str | Response:
    """Show the booking page and, when the form is valid, book the table."""
    service = make_booking_service()
    now = now_tehran()
    form = ReserveForm()
    if request.method == "POST" and form.validate_on_submit():
        try:
            reservation = service.reserve(
                form.to_request(get_active_language().code, _signed_in_user_id()), now
            )
            db.session.commit()
        except BookingError as error:
            db.session.rollback()
            message = get_translator()(f"reserve.error.{error.problem.value}")
            return _render_page(form, _choice_from_form(form, service, now), service, now, message)
        return redirect(url_for("public.reservation", public_token=reservation.public_token))
    if request.method == "POST":
        return _render_page(form, _choice_from_form(form, service, now), service, now)
    if current_user.is_authenticated:
        form.customer_name.data = current_user.display_name
        form.customer_phone.data = current_user.phone or ""
    choice = _choice_from_query(service, now)
    return _render_page(form, choice, service, now)


def _signed_in_user_id() -> int | None:
    """Return the id of the signed-in customer, or None for a guest."""
    return current_user.id if current_user.is_authenticated else None


def _find_or_404(public_token: str):  # noqa: ANN202
    """Return the reservation with this token or stop with 404."""
    reservation = make_booking_service().find_by_token(public_token)
    if reservation is None:
        abort(404)
    return reservation


@public_blueprint.get("/reservation/<public_token>")
def reservation(public_token: str) -> str:
    """Show a booking and its status. The unguessable token is the only key."""
    booking = _find_or_404(public_token)
    return render_template(
        "reservation.html",
        booking=booking,
        can_cancel=booking.ends_at > now_tehran() and booking.status.value != "cancelled",
    )


@public_blueprint.post("/reservation/<public_token>/cancel")
def cancel_reservation(public_token: str) -> Response:
    """Let the guest cancel their own booking."""
    booking = _find_or_404(public_token)
    try:
        make_booking_service().cancel(booking)
        db.session.commit()
    except BookingError:
        db.session.rollback()
    return redirect(url_for("public.reservation", public_token=public_token))
