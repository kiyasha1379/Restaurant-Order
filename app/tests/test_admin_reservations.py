"""Tables and reservations in the panel: permissions, the booking list, tables, hours, rules."""

from datetime import date, datetime, time

import pytest

from restaurant.constants import ReservationStatus, SettingKey
from restaurant.extensions import db
from restaurant.models import DiningTable, OpeningHour, Reservation, Setting, SpecialClosure
from restaurant.service_factory import make_booking_service
from restaurant.services import ReservationRequest
from tests.helpers import add_tables, staff_client

NOW = datetime(2026, 10, 26, 10, 0)  # a Monday, 10:00
TOMORROW = "2026-10-27"


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr("restaurant.blueprints.admin.reservations_routes.now_tehran", lambda: NOW)


@pytest.fixture
def tables(app):
    created = add_tables(2, 4, 6)
    db.session.commit()
    return [table.id for table in created]


def make_booking(table_id, start=time(19, 0), status=ReservationStatus.PENDING, guests=2):
    request = ReservationRequest(
        day=date(2026, 10, 27),
        start=start,
        guests=guests,
        table_id=table_id,
        customer_name="سارا احمدی",
        customer_phone="09123456789",
        language_code="fa",
    )
    booking = make_booking_service().reserve(request, NOW, by_staff=True, status=status)
    db.session.commit()
    return booking


@pytest.fixture
def manager(app):
    return staff_client(app, "manager")


# --- permissions ---------------------------------------------------------------------------------


def test_a_role_without_the_permission_is_refused(app, tables):
    client = staff_client(app, "kitchen")
    for path in ("/admin/reservations", "/admin/tables", "/admin/schedule"):
        assert client.get(path).status_code == 403


def test_view_only_staff_see_the_pages_but_cannot_change_anything(app, tables):
    booking = make_booking(tables[1])
    client = staff_client(app, "viewer")
    page = client.get("/admin/reservations").get_data(as_text=True)
    assert "سارا احمدی" in page and "رزرو دستی" not in page
    assert client.get("/admin/tables").status_code == 200
    assert client.get("/admin/schedule").status_code == 200
    assert client.get("/admin/reservations/new").status_code == 403
    assert client.post(f"/admin/reservations/{booking.id}/confirm").status_code == 403
    assert client.post(f"/admin/tables/{tables[0]}/delete").status_code == 403
    assert client.post("/admin/schedule/rules", data={}).status_code == 403
    assert db.session.get(Reservation, booking.id).status is ReservationStatus.PENDING


def test_the_sidebar_lists_the_section_for_those_who_may_open_it(app, tables):
    allowed = staff_client(app, "manager").get("/admin/reservations").get_data(as_text=True)
    assert 'href="/admin/reservations"' in allowed
    kitchen = staff_client(app, "kitchen").get("/admin/orders").get_data(as_text=True)
    assert 'href="/admin/reservations"' not in kitchen


# --- bookings -----------------------------------------------------------------------------------


def test_the_list_shows_upcoming_bookings_and_filters_by_day_and_status(manager, tables):
    make_booking(tables[1])
    make_booking(tables[2], start=time(20, 0), status=ReservationStatus.CONFIRMED)
    html = manager.get("/admin/reservations").get_data(as_text=True)
    assert html.count("سارا احمدی") == 2 and "منتظر پاسخ" in html
    only_confirmed = manager.get("/admin/reservations?status=confirmed").get_data(as_text=True)
    assert only_confirmed.count("سارا احمدی") == 1
    other_day = manager.get("/admin/reservations?day=2026-10-30").get_data(as_text=True)
    assert "سارا احمدی" not in other_day and "رزروی پیدا نشد" in other_day
    assert "سارا احمدی" in manager.get(f"/admin/reservations?day={TOMORROW}").get_data(as_text=True)


def test_a_bad_filter_value_is_ignored(manager, tables):
    assert manager.get("/admin/reservations?day=x&status=nope").status_code == 200


def test_confirm_and_cancel_change_the_status(manager, tables):
    booking = make_booking(tables[1])
    response = manager.post(f"/admin/reservations/{booking.id}/confirm")
    assert response.status_code == 302
    assert db.session.get(Reservation, booking.id).status is ReservationStatus.CONFIRMED
    manager.post(f"/admin/reservations/{booking.id}/cancel")
    assert db.session.get(Reservation, booking.id).status is ReservationStatus.CANCELLED


def test_confirming_a_booking_whose_table_is_taken_is_refused_with_a_reason(manager, tables):
    first, second = make_booking(tables[1]), make_booking(tables[1])
    manager.post(f"/admin/reservations/{first.id}/confirm")
    page = manager.get(f"/admin/reservations/{second.id}").get_data(as_text=True)
    assert "میز ۱" in page  # a free table is suggested
    response = manager.post(f"/admin/reservations/{second.id}/confirm", follow_redirects=True)
    assert "همین الان" in response.get_data(as_text=True) or "برداشت" in response.get_data(
        as_text=True
    )
    assert db.session.get(Reservation, second.id).status is ReservationStatus.PENDING


def test_a_booking_can_be_moved_to_a_suggested_table(manager, tables):
    booking = make_booking(tables[1])
    response = manager.post(
        f"/admin/reservations/{booking.id}/table", data={"table_id": str(tables[2])}
    )
    assert response.status_code == 302
    moved = db.session.get(Reservation, booking.id)
    assert moved.table_id == tables[2] and moved.table_label == "3"
    assert manager.post(f"/admin/reservations/{booking.id}/table", data={}).status_code == 400


def test_unknown_booking_is_not_found(manager, tables):
    assert manager.get("/admin/reservations/999").status_code == 404
    assert manager.post("/admin/reservations/999/confirm").status_code == 404


def booking_form(table_id, **overrides):
    data = {
        "date": TOMORROW,
        "time": "13:10",
        "guests": "2",
        "table_id": str(table_id),
        "status": "confirmed",
        "customer_name": "علی رضایی",
        "customer_phone": "۰۹۱۲۳۴۵۶۷۸۹",
        "note": "تولد",
    }
    data.update(overrides)
    return data


def test_staff_can_make_a_booking_at_any_time_inside_opening_hours(manager, tables):
    response = manager.post("/admin/reservations/new", data=booking_form(tables[0]))
    booking = db.session.query(Reservation).one()
    assert response.status_code == 302
    assert booking.status is ReservationStatus.CONFIRMED and booking.starts_at.minute == 10
    assert booking.customer_phone == "09123456789"


def test_the_manual_form_shows_errors_and_stores_nothing(manager, tables):
    for overrides in ({"date": ""}, {"time": "late"}, {"customer_phone": "12"}, {"guests": "0"}):
        response = manager.post(
            "/admin/reservations/new", data=booking_form(tables[0], **overrides)
        )
        assert response.status_code == 200 and "field__error" in response.get_data(as_text=True)
    outside = manager.post("/admin/reservations/new", data=booking_form(tables[0], time="08:00"))
    assert "بیرون از ساعت کاری" in outside.get_data(as_text=True)
    assert db.session.query(Reservation).count() == 0


def test_the_manual_form_page_opens_with_the_date_picker(manager, tables):
    html = manager.get("/admin/reservations/new").get_data(as_text=True)
    assert "data-date-field" in html and 'value="2026-10-26"' in html and 'id="site-config"' in html


# --- tables -------------------------------------------------------------------------------------


def test_tables_can_be_added_changed_and_reordered(manager, app):
    response = manager.post(
        "/admin/tables/new",
        data={"label": "A1", "capacity": "۴", "sort_order": "0", "is_active": "y"},
    )
    assert response.status_code == 302
    manager.post("/admin/tables/new", data={"label": "A2", "capacity": "2", "sort_order": "1"})
    first, second = db.session.query(DiningTable).order_by(DiningTable.id).all()
    assert first.capacity == 4 and first.is_active and not second.is_active
    manager.post(
        f"/admin/tables/{first.id}", data={"label": "B1", "capacity": "6", "is_active": "y"}
    )
    db.session.refresh(first)
    assert (first.label, first.capacity) == ("B1", 6)
    manager.post(f"/admin/tables/{second.id}/move/up")
    db.session.refresh(first)
    db.session.refresh(second)
    assert second.sort_order < first.sort_order
    manager.post(f"/admin/tables/{second.id}/active")
    db.session.refresh(second)
    assert second.is_active


@pytest.mark.parametrize(
    "data",
    [
        {"label": "", "capacity": "2"},
        {"label": "x" * 21, "capacity": "2"},
        {"label": "T", "capacity": "0"},
        {"label": "T", "capacity": "51"},
        {"label": "T", "capacity": ""},
        {"label": "1", "capacity": "2"},
    ],
)
def test_bad_table_data_is_refused(manager, tables, data):
    response = manager.post("/admin/tables/new", data=data)
    assert response.status_code == 200 and db.session.query(DiningTable).count() == 3


def test_a_table_with_live_bookings_cannot_be_deleted(manager, tables):
    make_booking(tables[1])
    response = manager.post(f"/admin/tables/{tables[1]}/delete", follow_redirects=True)
    assert "رزرو فعال پیش‌رو" in response.get_data(as_text=True)
    assert db.session.get(DiningTable, tables[1]) is not None
    manager.post(f"/admin/tables/{tables[0]}/delete")
    assert db.session.get(DiningTable, tables[0]) is None


def test_deleting_a_table_keeps_the_label_of_old_bookings(manager, tables):
    booking = make_booking(tables[1])
    manager.post(f"/admin/reservations/{booking.id}/cancel")
    manager.post(f"/admin/tables/{tables[1]}/delete")
    kept = db.session.get(Reservation, booking.id)
    assert kept.table_id is None and kept.table_label == "2"
    assert "۲" in manager.get(f"/admin/reservations/{booking.id}").get_data(as_text=True)


def test_unknown_table_is_not_found(manager, tables):
    assert manager.get("/admin/tables/999").status_code == 404
    assert manager.post("/admin/tables/999/delete").status_code == 404
    assert manager.post(f"/admin/tables/{tables[0]}/move/sideways").status_code == 404


# --- hours, closures, rules ---------------------------------------------------------------------


def hours_form(**overrides):
    data = {}
    for weekday in range(7):
        data[f"opens_{weekday}"] = "11:00"
        data[f"closes_{weekday}"] = "22:00"
    data.update(overrides)
    return data


def test_weekly_hours_are_saved_and_closed_days_have_no_slots(manager, tables):
    response = manager.post("/admin/schedule/hours", data=hours_form(closed_1="1", opens_2="09:30"))
    assert response.status_code == 302
    rows = {row.weekday: row for row in db.session.query(OpeningHour)}
    assert len(rows) == 7 and rows[1].is_closed and rows[2].opens_at == time(9, 30)
    page = manager.get("/admin/schedule").get_data(as_text=True)
    assert 'value="09:30"' in page and "checked" in page


@pytest.mark.parametrize("overrides", [{"closes_0": "10:00"}, {"opens_3": ""}, {"closes_4": "x"}])
def test_bad_hours_are_refused_and_nothing_changes(manager, tables, overrides):
    response = manager.post(
        "/admin/schedule/hours", data=hours_form(**overrides), follow_redirects=True
    )
    assert "ساعت بسته شدن باید بعد" in response.get_data(as_text=True)
    assert db.session.query(OpeningHour).count() == 0


def test_closing_days_can_be_added_and_removed(manager, tables):
    manager.post("/admin/schedule/closures", data={"date": TOMORROW, "reason": "تعمیرات"})
    closure = db.session.query(SpecialClosure).one()
    assert closure.day == date(2026, 10, 27) and closure.reason == "تعمیرات"
    assert "تعمیرات" in manager.get("/admin/schedule").get_data(as_text=True)
    duplicate = manager.post(
        "/admin/schedule/closures", data={"date": TOMORROW, "reason": ""}, follow_redirects=True
    )
    assert "قبلاً تعطیل شده" in duplicate.get_data(as_text=True)
    manager.post(f"/admin/schedule/closures/{closure.id}/delete")
    assert db.session.query(SpecialClosure).count() == 0


def test_a_closing_day_needs_a_real_date(manager, tables):
    response = manager.post("/admin/schedule/closures", data={"date": "", "reason": "x"})
    assert response.status_code == 200 and "field__error" in response.get_data(as_text=True)
    assert db.session.query(SpecialClosure).count() == 0


def test_reservation_rules_are_saved_and_used_by_the_public_page(manager, tables):
    data = {
        "max_advance_days": "10",
        "duration_minutes": "60",
        "slot_minutes": "15",
        "min_notice_minutes": "0",
        "auto_confirm": "y",
    }
    assert manager.post("/admin/schedule/rules", data=data).status_code == 302
    stored = {row.key: row.value for row in db.session.query(Setting)}
    assert stored[SettingKey.RESERVATION_MAX_ADVANCE_DAYS] == "10"
    assert stored[SettingKey.RESERVATION_AUTO_CONFIRM] == "1"
    page = manager.get("/admin/schedule").get_data(as_text=True)
    assert 'value="10"' in page and 'value="60"' in page


@pytest.mark.parametrize(
    "overrides",
    [
        {"max_advance_days": "0"},
        {"duration_minutes": "5"},
        {"slot_minutes": "500"},
        {"min_notice_minutes": ""},
    ],
)
def test_rules_outside_their_range_are_refused(manager, tables, overrides):
    data = {
        "max_advance_days": "30",
        "duration_minutes": "90",
        "slot_minutes": "30",
        "min_notice_minutes": "30",
    }
    data.update(overrides)
    response = manager.post("/admin/schedule/rules", data=data)
    assert response.status_code == 200 and "field__error" in response.get_data(as_text=True)
    assert db.session.query(Setting).count() == 0
