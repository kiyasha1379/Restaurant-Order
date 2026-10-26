"""Booking rules against a real database: opening hours, availability, overlap, confirmation."""

import threading
from datetime import date, datetime, time, timedelta

import pytest

from restaurant import create_app
from restaurant.constants import ReservationStatus, SettingKey
from restaurant.extensions import db
from restaurant.models import OpeningHour, Reservation, Setting, SpecialClosure
from restaurant.service_factory import (
    make_booking_service,
    make_schedule_service,
    make_site_settings_service,
)
from restaurant.services import BookingError, BookingProblem, ReservationRequest, TableState
from tests.conftest import add_two_languages
from tests.helpers import add_tables

NOW = datetime(2026, 10, 26, 10, 0)  # a Monday, 10:00
TODAY = NOW.date()
TOMORROW = TODAY + timedelta(days=1)


@pytest.fixture
def tables(app):
    created = add_tables(2, 4, 6)
    db.session.commit()
    return created


def request_for(table, day=TOMORROW, start=time(19, 0), guests=2, **fields) -> ReservationRequest:
    values = {
        "day": day,
        "start": start,
        "guests": guests,
        "table_id": table.id,
        "customer_name": "Sara",
        "customer_phone": "09123456789",
        "language_code": "fa",
    }
    return ReservationRequest(**{**values, **fields})


def reserve(table, **fields) -> Reservation:
    reservation = make_booking_service().reserve(request_for(table, **fields), NOW)
    db.session.commit()
    return reservation


def problem_of(call) -> BookingProblem:
    with pytest.raises(BookingError) as caught:
        call()
    db.session.rollback()
    return caught.value.problem


def confirm(reservation: Reservation) -> None:
    make_booking_service().confirm(reservation)
    db.session.commit()


# --- rules and settings ----------------------------------------------------------------------


def test_default_rules_and_stored_values(app) -> None:
    settings = make_site_settings_service()
    rules = settings.get_booking_rules()
    assert (rules.max_advance_days, rules.duration_minutes, rules.slot_minutes) == (30, 90, 30)
    assert (rules.min_notice_minutes, rules.auto_confirm) == (30, False)
    db.session.add_all(
        [
            Setting(key=SettingKey.RESERVATION_MAX_ADVANCE_DAYS, value="7"),
            Setting(key=SettingKey.RESERVATION_DURATION_MINUTES, value="120"),
            Setting(key=SettingKey.RESERVATION_AUTO_CONFIRM, value="1"),
        ]
    )
    db.session.commit()
    rules = settings.get_booking_rules()
    assert (rules.max_advance_days, rules.duration_minutes, rules.auto_confirm) == (7, 120, True)


@pytest.mark.parametrize("broken", ["abc", "0", "-4", "99999", ""])
def test_a_broken_rule_uses_its_default(app, broken) -> None:
    db.session.add(Setting(key=SettingKey.RESERVATION_MAX_ADVANCE_DAYS, value=broken))
    db.session.commit()
    assert make_site_settings_service().get_booking_rules().max_advance_days == 30


def test_rules_can_be_stored_and_read_back(app) -> None:
    from restaurant.services import BookingRules

    settings = make_site_settings_service()
    settings.set_booking_rules(BookingRules(10, 60, 15, 0, True))
    db.session.commit()
    assert settings.get_booking_rules() == BookingRules(10, 60, 15, 0, True)


# --- opening hours and start times ---------------------------------------------------------------


def test_without_stored_hours_the_default_hours_apply(app) -> None:
    hours = make_schedule_service().hours_on(TOMORROW)
    assert (hours.opens_at, hours.closes_at) == (time(12, 0), time(23, 0))


def test_closed_weekdays_and_closing_days_have_no_hours(app) -> None:
    schedule = make_schedule_service()
    schedule.set_hours(TOMORROW.weekday(), time(12), time(23), True)
    schedule.add_closure(TODAY, "Holiday")
    db.session.commit()
    assert schedule.hours_on(TOMORROW) is None and schedule.hours_on(TODAY) is None
    assert schedule.hours_on(TODAY + timedelta(days=2)) is not None
    assert schedule.closed_days_between(TODAY, TODAY + timedelta(days=2)) == [TODAY, TOMORROW]


def test_hours_must_close_after_they_open(app) -> None:
    from restaurant.services import InvalidHoursError

    with pytest.raises(InvalidHoursError):
        make_schedule_service().set_hours(0, time(20), time(20), False)


def test_a_day_cannot_be_closed_twice_and_can_be_opened_again(app) -> None:
    from restaurant.services import DuplicateClosureError

    schedule = make_schedule_service()
    closure = schedule.add_closure(TOMORROW, " Event ")
    db.session.commit()
    assert closure.reason == "Event"
    with pytest.raises(DuplicateClosureError):
        schedule.add_closure(TOMORROW, "again")
    db.session.rollback()
    schedule.remove_closure(closure.id)
    schedule.remove_closure(99999)
    db.session.commit()
    assert db.session.query(SpecialClosure).count() == 0


def test_start_times_follow_the_slot_step_and_end_before_closing(app) -> None:
    rules = make_site_settings_service().get_booking_rules()
    times = make_schedule_service().start_times(TOMORROW, rules, NOW)
    assert times[0] == time(12, 0) and times[-1] == time(21, 30)  # 21:30 + 90 min = 23:00
    assert len(times) == 20


def test_start_times_today_respect_the_minimum_notice(app) -> None:
    rules = make_site_settings_service().get_booking_rules()
    times = make_schedule_service().start_times(TODAY, rules, datetime(2026, 10, 26, 13, 10))
    assert times[0] == time(14, 0)
    assert make_schedule_service().start_times(TODAY, rules, datetime(2026, 10, 26, 22, 0)) == []


# --- availability -------------------------------------------------------------------------


def test_day_availability_counts_suitable_free_tables(app, tables) -> None:
    service = make_booking_service()
    two = service.day_availability(TOMORROW, 2, NOW)
    five = service.day_availability(TOMORROW, 5, NOW)
    assert two.is_open and two.slots[0].free_tables == 3
    assert five.slots[0].free_tables == 1  # only the six-seat table


def test_a_confirmed_booking_removes_its_table_only_while_it_overlaps(app, tables) -> None:
    confirm(reserve(tables[1], start=time(19, 0)))
    service = make_booking_service()
    day = service.day_availability(TOMORROW, 4, NOW)
    free = {slot.start: slot.free_tables for slot in day.slots}
    assert free[time(18, 0)] == 1 and free[time(19, 0)] == 1  # 18:00 + 90 min overlaps 19:00
    assert free[time(20, 0)] == 1 and free[time(20, 30)] == 2  # 19:00-20:30 ends at 20:30
    assert free[time(17, 30)] == 2  # 17:30-19:00 ends exactly when the booking starts


def test_pending_bookings_do_not_hold_a_table(app, tables) -> None:
    reserve(tables[1])
    states = make_booking_service().tables_at(TOMORROW, time(19, 0), 2, NOW)
    assert [a.state for a in states] == [TableState.FREE] * 3


def test_tables_at_marks_busy_and_too_small_tables(app, tables) -> None:
    confirm(reserve(tables[1]))
    states = make_booking_service().tables_at(TOMORROW, time(19, 0), 3, NOW)
    assert [a.state for a in states] == [TableState.TOO_SMALL, TableState.BUSY, TableState.FREE]


def test_inactive_tables_are_not_offered(app, tables) -> None:
    tables[0].is_active = False
    db.session.commit()
    labels = [a.table.label for a in make_booking_service().tables_at(TOMORROW, time(19), 2, NOW)]
    assert labels == ["2", "3"]


def test_closed_or_far_days_have_no_slots(app, tables) -> None:
    make_schedule_service().add_closure(TOMORROW, "")
    db.session.commit()
    service = make_booking_service()
    assert not service.day_availability(TOMORROW, 2, NOW).is_open
    assert not service.day_availability(TODAY + timedelta(days=31), 2, NOW).is_open
    assert not service.day_availability(TODAY - timedelta(days=1), 2, NOW).is_open
    assert service.bookable_window(NOW) == (TODAY, TODAY + timedelta(days=30))


def test_max_guests_is_the_biggest_active_table(app, tables) -> None:
    assert make_booking_service().max_guests() == 6
    tables[2].is_active = False
    db.session.commit()
    assert make_booking_service().max_guests() == 4


# --- making a booking --------------------------------------------------------------------------


def test_a_guest_booking_waits_for_confirmation(app, tables) -> None:
    booking = reserve(tables[1], guests=3, note=" window ")
    assert booking.status is ReservationStatus.PENDING and not booking.holds_table
    assert booking.table_label == "2" and booking.note == "window"
    assert booking.ends_at - booking.starts_at == timedelta(minutes=90)
    assert len(booking.public_token) >= 10


def test_the_rules_can_confirm_automatically(app, tables) -> None:
    db.session.add(Setting(key=SettingKey.RESERVATION_AUTO_CONFIRM, value="1"))
    db.session.commit()
    assert reserve(tables[0]).status is ReservationStatus.CONFIRMED


@pytest.mark.parametrize(
    ("fields", "problem"),
    [
        ({"day": TODAY - timedelta(days=1)}, BookingProblem.PAST),
        ({"day": TODAY + timedelta(days=31)}, BookingProblem.TOO_FAR),
        ({"start": time(11, 0)}, BookingProblem.OUTSIDE_HOURS),
        ({"start": time(22, 0)}, BookingProblem.OUTSIDE_HOURS),
        ({"start": time(19, 10)}, BookingProblem.BAD_TIME),
        ({"day": TODAY, "start": time(10, 30)}, BookingProblem.OUTSIDE_HOURS),
        ({"guests": 0}, BookingProblem.BAD_GUESTS),
        ({"guests": 7}, BookingProblem.BAD_GUESTS),
    ],
)
def test_bad_bookings_are_refused_and_nothing_is_stored(app, tables, fields, problem) -> None:
    got = problem_of(lambda: make_booking_service().reserve(request_for(tables[2], **fields), NOW))
    assert got is problem
    assert db.session.query(Reservation).count() == 0


def test_a_start_inside_the_notice_time_is_past(app, tables) -> None:
    late = datetime(2026, 10, 26, 13, 0)  # 13:15 is less than 30 minutes away
    request = request_for(tables[0], day=TODAY, start=time(13, 15))
    assert problem_of(lambda: make_booking_service().reserve(request, late)) is BookingProblem.PAST


def test_closed_day_is_refused(app, tables) -> None:
    make_schedule_service().add_closure(TOMORROW, "")
    db.session.commit()
    assert problem_of(lambda: make_booking_service().reserve(request_for(tables[0]), NOW)) is (
        BookingProblem.CLOSED
    )


def test_unknown_inactive_and_small_tables_are_refused(app, tables) -> None:
    service = make_booking_service()
    unknown = request_for(tables[0], table_id=9999)
    assert problem_of(lambda: service.reserve(unknown, NOW)) is BookingProblem.NO_TABLE
    tables[0].is_active = False
    db.session.commit()
    assert problem_of(lambda: service.reserve(request_for(tables[0]), NOW)) is (
        BookingProblem.NO_TABLE
    )
    assert problem_of(lambda: service.reserve(request_for(tables[0], guests=3), NOW)) is (
        BookingProblem.NO_TABLE
    )
    assert problem_of(lambda: service.reserve(request_for(tables[1], guests=5), NOW)) is (
        BookingProblem.TABLE_TOO_SMALL
    )


def test_a_confirmed_booking_blocks_overlapping_bookings(app, tables) -> None:
    confirm(reserve(tables[1], start=time(19, 0)))
    service = make_booking_service()
    assert problem_of(lambda: service.reserve(request_for(tables[1], start=time(20, 0)), NOW)) is (
        BookingProblem.TABLE_TAKEN
    )
    assert reserve(tables[1], start=time(20, 30)).status is ReservationStatus.PENDING
    assert reserve(tables[2], start=time(19, 0)).table_label == "3"


def test_two_pending_bookings_may_overlap_but_only_one_can_be_confirmed(app, tables) -> None:
    first, second = reserve(tables[1]), reserve(tables[1])
    confirm(first)
    assert problem_of(lambda: make_booking_service().confirm(second)) is BookingProblem.TABLE_TAKEN
    assert second.status is ReservationStatus.PENDING
    alternatives = make_booking_service().alternatives_for(second)
    assert [table.label for table in alternatives] == ["1", "3"]


def test_staff_may_skip_notice_window_and_choose_the_status(app, tables) -> None:
    service = make_booking_service()
    walk_in = request_for(tables[0], day=TODAY, start=time(12, 10))
    booking = service.reserve(walk_in, NOW, by_staff=True, status=ReservationStatus.CONFIRMED)
    far = request_for(tables[1], day=TODAY + timedelta(days=60), start=time(19, 10))
    service.reserve(far, NOW, by_staff=True)
    db.session.commit()
    assert booking.status is ReservationStatus.CONFIRMED
    closed = make_schedule_service()
    closed.add_closure(TOMORROW, "")
    db.session.commit()
    assert problem_of(lambda: service.reserve(request_for(tables[0]), NOW, by_staff=True)) is (
        BookingProblem.CLOSED
    )


# --- confirming, cancelling, moving ---


def test_cancel_frees_the_table_and_cannot_repeat(app, tables) -> None:
    booking = reserve(tables[1])
    confirm(booking)
    make_booking_service().cancel(booking)
    db.session.commit()
    assert booking.status is ReservationStatus.CANCELLED
    assert reserve(tables[1]).table_label == "2"
    assert problem_of(lambda: make_booking_service().cancel(booking)) is (
        BookingProblem.ALREADY_CANCELLED
    )
    assert problem_of(lambda: make_booking_service().confirm(booking)) is BookingProblem.NOT_PENDING


def test_confirm_needs_a_pending_booking(app, tables) -> None:
    booking = reserve(tables[1])
    confirm(booking)
    assert problem_of(lambda: make_booking_service().confirm(booking)) is BookingProblem.NOT_PENDING


def test_change_table_checks_capacity_and_overlap(app, tables) -> None:
    taken = reserve(tables[2])
    confirm(taken)
    booking = reserve(tables[1], guests=4)
    service = make_booking_service()
    assert problem_of(lambda: service.change_table(booking, tables[0].id)) is (
        BookingProblem.TABLE_TOO_SMALL
    )
    assert problem_of(lambda: service.change_table(booking, tables[2].id)) is (
        BookingProblem.TABLE_TAKEN
    )
    assert problem_of(lambda: service.change_table(booking, 9999)) is BookingProblem.NO_TABLE
    taken_first = reserve(tables[1], guests=2, start=time(12, 0), day=TOMORROW)
    service.change_table(taken_first, tables[0].id)
    db.session.commit()
    assert taken_first.table_label == "1"


def test_a_booking_keeps_its_table_label_when_the_table_is_deleted(app, tables) -> None:
    booking = reserve(tables[1])
    db.session.delete(tables[1])
    db.session.commit()
    db.session.refresh(booking)
    assert booking.table_id is None and booking.table_label == "2"


# --- simultaneous requests ---


def test_two_simultaneous_requests_cannot_both_get_the_table(tmp_path) -> None:
    """Both threads check, then insert; the write lock makes the second one see the first."""
    app = create_app(
        "test",
        {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'race.db'}", "UPLOAD_FOLDER": tmp_path},
    )
    with app.app_context():
        db.create_all()
        add_two_languages()
        table = add_tables(4)[0]
        db.session.add(Setting(key=SettingKey.RESERVATION_AUTO_CONFIRM, value="1"))
        db.session.commit()
        table_id = table.id
        db.session.remove()

    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def attempt() -> None:
        with app.app_context():
            service = make_booking_service()
            barrier.wait()
            try:
                service.reserve(
                    ReservationRequest(
                        day=TOMORROW,
                        start=time(19, 0),
                        guests=2,
                        table_id=table_id,
                        customer_name="X",
                        customer_phone="09123456789",
                        language_code="fa",
                    ),
                    NOW,
                )
                threading.Event().wait(0.4)  # keep the lock while the other request waits
                db.session.commit()
                outcomes.append("booked")
            except BookingError as error:
                db.session.rollback()
                outcomes.append(error.problem.value)
            finally:
                db.session.remove()

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert sorted(outcomes) == ["booked", "table_taken"]
    with app.app_context():
        assert db.session.query(Reservation).count() == 1
        db.session.remove()
        db.drop_all()


def test_opening_hours_table_has_one_row_per_weekday(app) -> None:
    schedule = make_schedule_service()
    schedule.set_hours(0, time(10), time(20), False)
    schedule.set_hours(0, time(11), time(21), False)
    db.session.commit()
    rows = db.session.query(OpeningHour).all()
    assert len(rows) == 1 and rows[0].opens_at == time(11, 0)
    assert isinstance(date.today(), date)
