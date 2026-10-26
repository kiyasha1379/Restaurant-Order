"""Tables and reservations: the booking list, manual bookings, tables, hours and the rules."""

from flask import abort, flash, redirect, render_template, request, url_for
from werkzeug.wrappers import Response

from restaurant.blueprints.admin import admin_blueprint
from restaurant.blueprints.admin.guards import permission_required
from restaurant.booking_web import parse_day
from restaurant.constants import (
    WEEKDAYS_SATURDAY_FIRST,
    AccessLevel,
    PermissionKey,
    ReservationStatus,
)
from restaurant.extensions import db
from restaurant.formatting import WEEKDAY_NAMES
from restaurant.forms.admin_booking_forms import (
    ClosureForm,
    ManualReservationForm,
    RulesForm,
    TableForm,
    read_weekly_hours,
)
from restaurant.language_context import get_active_language, get_translator
from restaurant.service_factory import (
    make_booking_service,
    make_schedule_service,
    make_site_settings_service,
    make_table_admin_service,
)
from restaurant.services import (
    BookingError,
    DuplicateClosureError,
    DuplicateTableLabelError,
    InvalidHoursError,
    InvalidTableError,
    TableInUseError,
)
from restaurant.timeutils import now_tehran

TABLES = PermissionKey.TABLES
EDIT = AccessLevel.EDIT
DIRECTIONS = {"up": -1, "down": 1}
TABLE_ERROR_KEYS = {
    InvalidTableError: "admin.tables.error.label",
    DuplicateTableLabelError: "admin.tables.error.duplicate",
    TableInUseError: "admin.tables.error.in_use",
}


def _booking_error_text(error: BookingError) -> str:
    """Return the message for a refused booking change, in the panel language."""
    return get_translator()(f"reserve.error.{error.problem.value}")


def _status_from_query() -> ReservationStatus | None:
    """Read the status filter; an unknown value means "any"."""
    try:
        return ReservationStatus(request.args["status"])
    except (KeyError, ValueError):
        return None


# --- bookings --------------------------------------------------------------------------------


@admin_blueprint.get("/reservations")
@permission_required(TABLES)
def reservations() -> str:
    """List bookings: one day (`?day=`) or everything from today onwards, by status."""
    now = now_tehran()
    day = parse_day(request.args.get("day", ""))
    status = _status_from_query()
    service = make_booking_service()
    return render_template(
        "admin/reservations/list.html",
        bookings=service.list_for_admin(day=day, status=status, now=now),
        day=day,
        status=status,
        statuses=list(ReservationStatus),
        waiting=service.count_waiting(now),
        today=now.date(),
    )


@admin_blueprint.get("/reservations/<int:reservation_id>")
@permission_required(TABLES)
def reservation_detail(reservation_id: int) -> str:
    """Show one booking with its actions and the tables that could take it."""
    service = make_booking_service()
    booking = service.get_reservation(reservation_id)
    if booking is None:
        abort(404)
    alternatives = (
        service.alternatives_for(booking)
        if booking.status is not ReservationStatus.CANCELLED
        else []
    )
    return render_template(
        "admin/reservations/detail.html", booking=booking, alternatives=alternatives
    )


def _change_booking(reservation_id: int, action) -> Response:  # noqa: ANN001 - (service, booking)
    """Load the booking, apply `action`, save, and report a refused change."""
    service = make_booking_service()
    booking = service.get_reservation(reservation_id)
    if booking is None:
        abort(404)
    try:
        action(service, booking)
        db.session.commit()
    except BookingError as error:
        db.session.rollback()
        flash(_booking_error_text(error), "error")
    else:
        flash(get_translator()("admin.saved"), "success")
    target = request.form.get("next", "")
    if target.startswith("/admin/"):
        return redirect(target)
    return redirect(url_for("admin.reservation_detail", reservation_id=reservation_id))


@admin_blueprint.post("/reservations/<int:reservation_id>/confirm")
@permission_required(TABLES, EDIT)
def reservation_confirm(reservation_id: int) -> Response:
    """Confirm a waiting booking (refused when a confirmed one holds the table)."""
    return _change_booking(reservation_id, lambda service, booking: service.confirm(booking))


@admin_blueprint.post("/reservations/<int:reservation_id>/cancel")
@permission_required(TABLES, EDIT)
def reservation_cancel(reservation_id: int) -> Response:
    """Cancel a booking."""
    return _change_booking(reservation_id, lambda service, booking: service.cancel(booking))


@admin_blueprint.post("/reservations/<int:reservation_id>/table")
@permission_required(TABLES, EDIT)
def reservation_table(reservation_id: int) -> Response:
    """Move a booking to another table."""
    table_id = request.form.get("table_id", "")
    if not table_id.isdecimal():
        abort(400)
    return _change_booking(
        reservation_id, lambda service, booking: service.change_table(booking, int(table_id))
    )


@admin_blueprint.route("/reservations/new", methods=["GET", "POST"])
@permission_required(TABLES, EDIT)
def reservation_new() -> str | Response:
    """Make a booking for a guest who phoned or walked in; staff may use any time of the day."""
    service = make_booking_service()
    form = ManualReservationForm()
    form.set_table_choices(
        [(table.id, f"{table.label} ({table.capacity})") for table in service.list_tables()]
    )
    now = now_tehran()
    if request.method == "GET":
        form.date.data = now.date().isoformat()
    elif form.validate_on_submit():
        try:
            booking = service.reserve(
                form.to_request(get_active_language().code),
                now,
                by_staff=True,
                status=form.chosen_status,
            )
            db.session.commit()
        except BookingError as error:
            db.session.rollback()
            flash(_booking_error_text(error), "error")
        else:
            flash(get_translator()("admin.saved"), "success")
            return redirect(url_for("admin.reservation_detail", reservation_id=booking.id))
    return render_template(
        "admin/reservations/new.html", form=form, chosen_date=parse_day(form.date.data or "")
    )


# --- tables ------------------------------------------------------------------------------------


@admin_blueprint.get("/tables")
@permission_required(TABLES)
def tables() -> str:
    """List the tables of the hall with how many live bookings each has."""
    service = make_table_admin_service()
    now = now_tehran()
    rows = [(table, service.count_upcoming(table, now)) for table in service.list_tables()]
    return render_template("admin/reservations/tables.html", rows=rows)


def _table_form_page(form: TableForm, table=None) -> str:  # noqa: ANN001 - a DiningTable or None
    """Render the table form page."""
    return render_template("admin/reservations/table_form.html", form=form, table=table)


@admin_blueprint.route("/tables/new", methods=["GET", "POST"])
@permission_required(TABLES, EDIT)
def table_new() -> str | Response:
    """Add a table."""
    form = TableForm()
    if form.validate_on_submit():
        try:
            make_table_admin_service().create_table(form.to_input())
            db.session.commit()
        except (InvalidTableError, DuplicateTableLabelError) as error:
            db.session.rollback()
            flash(get_translator()(TABLE_ERROR_KEYS[type(error)]), "error")
        else:
            flash(get_translator()("admin.saved"), "success")
            return redirect(url_for("admin.tables"))
    return _table_form_page(form)


@admin_blueprint.route("/tables/<int:table_id>", methods=["GET", "POST"])
@permission_required(TABLES, EDIT)
def table_edit(table_id: int) -> str | Response:
    """Change a table."""
    service = make_table_admin_service()
    table = service.get_table(table_id)
    if table is None:
        abort(404)
    form = TableForm(obj=table)
    if form.validate_on_submit():
        try:
            service.update_table(table, form.to_input())
            db.session.commit()
        except (InvalidTableError, DuplicateTableLabelError) as error:
            db.session.rollback()
            flash(get_translator()(TABLE_ERROR_KEYS[type(error)]), "error")
        else:
            flash(get_translator()("admin.saved"), "success")
            return redirect(url_for("admin.tables"))
    return _table_form_page(form, table)


def _with_table(table_id: int, action) -> Response:  # noqa: ANN001 - (service, table)
    """Load the table, apply `action`, save, and report a refused change."""
    service = make_table_admin_service()
    table = service.get_table(table_id)
    if table is None:
        abort(404)
    try:
        action(service, table)
        db.session.commit()
    except TableInUseError as error:
        db.session.rollback()
        flash(get_translator()(TABLE_ERROR_KEYS[type(error)]), "error")
    return redirect(url_for("admin.tables"))


@admin_blueprint.post("/tables/<int:table_id>/delete")
@permission_required(TABLES, EDIT)
def table_delete(table_id: int) -> Response:
    """Remove a table that has no live bookings ahead."""
    return _with_table(table_id, lambda service, table: service.delete_table(table, now_tehran()))


@admin_blueprint.post("/tables/<int:table_id>/active")
@permission_required(TABLES, EDIT)
def table_toggle(table_id: int) -> Response:
    """Take a table out of use or put it back."""
    return _with_table(
        table_id, lambda service, table: service.set_active(table, not table.is_active)
    )


@admin_blueprint.post("/tables/<int:table_id>/move/<direction>")
@permission_required(TABLES, EDIT)
def table_move(table_id: int, direction: str) -> Response:
    """Move a table up or down on the floor plan."""
    if direction not in DIRECTIONS:
        abort(404)
    return _with_table(
        table_id, lambda service, table: service.move_table(table, DIRECTIONS[direction])
    )


# --- hours, closing days and rules ---------------------------------------------------------------


@admin_blueprint.get("/schedule")
@permission_required(TABLES)
def schedule() -> str:
    """Show the weekly hours, the closing days and the reservation rules."""
    return _schedule_page()


def _schedule_page(
    closure_form: ClosureForm | None = None, rules_form: RulesForm | None = None
) -> str:
    """Render the schedule page, with forms that may carry errors from a failed save."""
    service = make_schedule_service()
    now = now_tehran()
    code = get_active_language().code
    rules = make_site_settings_service().get_booking_rules()
    if rules_form is None:
        rules_form = RulesForm(
            data={
                "max_advance_days": rules.max_advance_days,
                "duration_minutes": rules.duration_minutes,
                "slot_minutes": rules.slot_minutes,
                "min_notice_minutes": rules.min_notice_minutes,
                "auto_confirm": rules.auto_confirm,
            }
        )
    return render_template(
        "admin/reservations/schedule.html",
        hours=service.list_hours(),
        weekdays=[
            (number, WEEKDAY_NAMES.get(code, WEEKDAY_NAMES["en"])[number])
            for number in WEEKDAYS_SATURDAY_FIRST
        ],
        closures=service.list_closures(now.date()),
        closure_form=closure_form or ClosureForm(),
        rules_form=rules_form,
        today=now.date(),
    )


@admin_blueprint.post("/schedule/hours")
@permission_required(TABLES, EDIT)
def schedule_hours() -> Response:
    """Save the opening hours of the whole week."""
    rows, broken = read_weekly_hours(request.form)
    service = make_schedule_service()
    try:
        if broken:
            raise InvalidHoursError(str(sorted(broken)))
        for weekday, opens_at, closes_at, is_closed in rows:
            service.set_hours(weekday, opens_at, closes_at, is_closed)
        db.session.commit()
    except InvalidHoursError:
        db.session.rollback()
        flash(get_translator()("admin.schedule.error.hours"), "error")
    else:
        flash(get_translator()("admin.saved"), "success")
    return redirect(url_for("admin.schedule"))


@admin_blueprint.post("/schedule/closures")
@permission_required(TABLES, EDIT)
def schedule_closure_add() -> str | Response:
    """Close a day."""
    form = ClosureForm()
    if form.validate_on_submit():
        try:
            make_schedule_service().add_closure(form.day, form.reason.data)
            db.session.commit()
        except DuplicateClosureError:
            db.session.rollback()
            flash(get_translator()("admin.schedule.error.duplicate"), "error")
        else:
            flash(get_translator()("admin.saved"), "success")
            return redirect(url_for("admin.schedule"))
    return _schedule_page(closure_form=form)


@admin_blueprint.post("/schedule/closures/<int:closure_id>/delete")
@permission_required(TABLES, EDIT)
def schedule_closure_remove(closure_id: int) -> Response:
    """Open a closed day again."""
    make_schedule_service().remove_closure(closure_id)
    db.session.commit()
    flash(get_translator()("admin.deleted"), "success")
    return redirect(url_for("admin.schedule"))


@admin_blueprint.post("/schedule/rules")
@permission_required(TABLES, EDIT)
def schedule_rules() -> str | Response:
    """Save the reservation rules."""
    form = RulesForm()
    if form.validate_on_submit():
        make_site_settings_service().set_booking_rules(form.to_rules())
        db.session.commit()
        flash(get_translator()("admin.saved"), "success")
        return redirect(url_for("admin.schedule"))
    return _schedule_page(rules_form=form)
