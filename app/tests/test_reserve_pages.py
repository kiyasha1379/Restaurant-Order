"""The reservation page, the availability API, the confirmation page and cancelling."""

from datetime import datetime, time

import pytest

from restaurant.constants import ReservationStatus
from restaurant.extensions import db
from restaurant.models import Reservation
from restaurant.service_factory import make_booking_service
from restaurant.services import ReservationRequest
from tests.helpers import add_tables

NOW = datetime(2026, 10, 26, 10, 0)  # a Monday, 10:00
TODAY, TOMORROW = "2026-10-26", "2026-10-27"


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    """The pages and the API read the clock from their own modules."""
    monkeypatch.setattr("restaurant.blueprints.public.reserve_routes.now_tehran", lambda: NOW)
    monkeypatch.setattr("restaurant.blueprints.api.now_tehran", lambda: NOW)


@pytest.fixture
def tables(app):
    created = add_tables(2, 4, 6)
    db.session.commit()
    return [table.id for table in created]


def booking_form(chosen_table, **fields):
    values = {
        "date": TOMORROW,
        "time": "19:00",
        "guests": "2",
        "table_id": str(chosen_table),
        "customer_name": "سارا احمدی",
        "customer_phone": "۰۹۱۲۳۴۵۶۷۸۹",
        "note": "",
    }
    return {**values, **fields}


def hold_table(table_id, day=TOMORROW, start=time(19, 0)):
    """Confirm a booking directly through the service."""
    service = make_booking_service()
    request = ReservationRequest(
        day=datetime.fromisoformat(day).date(),
        start=start,
        guests=2,
        table_id=table_id,
        customer_name="X",
        customer_phone="09123456789",
        language_code="fa",
    )
    booking = service.reserve(request, NOW, by_staff=True, status=ReservationStatus.CONFIRMED)
    db.session.commit()
    return booking


# --- the page ----------------------------------------------------------------------------


def test_the_page_shows_days_tables_and_the_first_free_day(client, tables):
    html = client.get("/fa/reserve").get_data(as_text=True)
    assert "رزرو میز" in html and "data-reserve-form" in html
    assert f'name="date" value="{TODAY}"' in html
    assert html.count("data-plan-table") == 3
    assert 'data-state="idle"' in html and 'data-state="free"' not in html
    for quick_day in (TODAY, TOMORROW, "2026-10-28"):
        assert f'data-day="{quick_day}"' in html
    assert 'name="time" value="12:00"' in html and 'name="time" value="21:30"' in html


def test_the_page_is_linked_in_the_navigation_and_marked_current(client, tables):
    html = client.get("/fa/reserve").get_data(as_text=True)
    assert 'href="/fa/reserve" aria-current="page"' in html


def test_choices_in_the_address_are_shown(client, tables):
    url = f"/fa/reserve?date={TOMORROW}&time=19:00&guests=3&table={tables[1]}"
    html = client.get(url).get_data(as_text=True)
    assert f'name="date" value="{TOMORROW}"' in html and 'name="guests" value="3"' in html
    assert 'value="19:00" checked' in html
    assert f'value="{tables[1]}" checked' in html
    assert "میز ۲" in html
    # A 2-seat table is too small for 3 guests and cannot be picked.
    assert 'data-state="too_small"' in html


def test_a_taken_table_is_disabled_and_a_chosen_one_that_is_taken_is_dropped(client, tables):
    hold_table(tables[1])
    html = client.get(f"/fa/reserve?date={TOMORROW}&time=19:00&table={tables[1]}").get_data(
        as_text=True
    )
    assert 'data-state="busy"' in html and f'value="{tables[1]}" checked' not in html


def test_a_day_outside_the_window_falls_back_to_the_first_free_day(client, tables):
    html = client.get("/fa/reserve?date=2027-05-01").get_data(as_text=True)
    assert f'name="date" value="{TODAY}"' in html


def test_nonsense_in_the_address_is_ignored(client, tables):
    response = client.get("/fa/reserve?date=x&time=99&guests=abc&table=zz")
    assert response.status_code == 200


def test_the_guest_count_is_kept_within_the_biggest_table(client, tables):
    html = client.get("/fa/reserve?guests=40").get_data(as_text=True)
    assert 'name="guests" value="6"' in html


def test_english_page_is_left_to_right_with_english_texts(client, tables):
    html = client.get("/en/reserve").get_data(as_text=True)
    assert 'dir="ltr"' in html and "Reserve a table" in html and "Seats 4" in html


def test_closed_days_are_listed_for_the_calendar_and_quick_days_are_disabled(client, tables):
    from restaurant.service_factory import make_schedule_service

    make_schedule_service().add_closure(datetime(2026, 10, 27).date(), "Holiday")
    db.session.commit()
    html = client.get("/fa/reserve").get_data(as_text=True)
    assert "&#34;2026-10-27&#34;" in html or '"2026-10-27"' in html
    assert f'data-day="{TOMORROW}" aria-pressed="false" disabled' in html


def test_the_page_without_tables_says_so(client, app):
    html = client.get("/fa/reserve").get_data(as_text=True)
    assert "هنوز میزی تعریف نشده است" in html


# --- the availability API ---------------------------------------------------------------


def test_availability_lists_slots_and_free_counts(client, tables):
    data = client.get(f"/api/availability?date={TOMORROW}&guests=5").get_json()
    assert data["open"] and data["max_guests"] == 6 and data["tables"] == []
    assert data["slots"][0] == {"time": "12:00", "label": "۱۲:۰۰", "free": 1, "available": True}


def test_availability_with_a_time_lists_table_states(client, tables):
    hold_table(tables[1])
    data = client.get(f"/api/availability?date={TOMORROW}&guests=3&time=19:00").get_json()
    states = {entry["id"]: entry["state"] for entry in data["tables"]}
    assert states == {tables[0]: "too_small", tables[1]: "busy", tables[2]: "free"}
    assert data["time_problem"] == ""


def test_availability_reports_a_time_that_cannot_be_booked(client, tables):
    data = client.get(f"/api/availability?date={TOMORROW}&guests=2&time=19:10").get_json()
    assert data["tables"] == [] and data["time_problem"] == "bad_time"


def test_availability_in_english_uses_latin_digits(client, tables):
    data = client.get(f"/api/availability?date={TOMORROW}&guests=2&lang=en").get_json()
    assert data["slots"][0]["label"] == "12:00"


@pytest.mark.parametrize(
    "query",
    [
        "date=nope&guests=2",
        f"date={TOMORROW}&guests=0",
        f"date={TOMORROW}&guests=7",
        f"date={TOMORROW}&guests=x",
        f"date={TOMORROW}&guests=2&time=late",
    ],
)
def test_availability_refuses_bad_input(client, tables, query):
    response = client.get(f"/api/availability?{query}")
    assert response.status_code == 400 and response.get_json()["error"]


def test_availability_for_a_day_beyond_the_window_has_no_slots(client, tables):
    data = client.get("/api/availability?date=2027-03-01&guests=2").get_json()
    assert data["open"] is False and data["slots"] == []


# --- booking -------------------------------------------------------------------------------


def test_a_valid_booking_waits_for_confirmation_and_opens_its_page(client, tables):
    response = client.post("/fa/reserve", data=booking_form(tables[1]))
    booking = db.session.query(Reservation).one()
    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/fa/reservation/{booking.public_token}")
    assert booking.status is ReservationStatus.PENDING and booking.table_label == "2"
    assert booking.customer_phone == "09123456789"
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "در انتظار تأیید" in page and "سارا احمدی" in page


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"date": ""}, "یک روز انتخاب کنید"),
        ({"time": ""}, "یک ساعت انتخاب کنید"),
        ({"table_id": ""}, "یک میز انتخاب کنید"),
        ({"customer_name": ""}, None),
        ({"customer_phone": "123"}, None),
        ({"guests": "0"}, "تعداد نفرات"),
    ],
)
def test_an_incomplete_booking_shows_the_errors_and_stores_nothing(client, tables, fields, message):
    response = client.post("/fa/reserve", data=booking_form(tables[1], **fields))
    html = response.get_data(as_text=True)
    assert response.status_code == 200 and "field__error" in html
    if message:
        assert message in html
    assert db.session.query(Reservation).count() == 0


def test_the_form_keeps_what_was_typed_after_an_error(client, tables):
    html = client.post(
        "/fa/reserve", data=booking_form(tables[1], customer_phone="123", note="کنار پنجره")
    ).get_data(as_text=True)
    assert "سارا احمدی" in html and "کنار پنجره" in html


def test_a_table_taken_in_the_meantime_gives_a_clear_message(client, tables):
    hold_table(tables[1])
    response = client.post("/fa/reserve", data=booking_form(tables[1]))
    html = response.get_data(as_text=True)
    assert response.status_code == 200 and "کس دیگری این میز را برداشت" in html
    assert 'data-state="busy"' in html and db.session.query(Reservation).count() == 1


def test_a_past_or_closed_booking_is_refused_with_its_reason(client, tables):
    past = client.post("/fa/reserve", data=booking_form(tables[1], date=TODAY, time="10:30"))
    assert "بیرون از ساعت کاری" in past.get_data(as_text=True)
    far = client.post("/fa/reserve", data=booking_form(tables[1], date="2027-03-01"))
    assert "بیرون از بازه" in far.get_data(as_text=True)
    assert db.session.query(Reservation).count() == 0


def test_the_booking_is_remembered_in_the_page_language(client, tables):
    client.post("/en/reserve", data=booking_form(tables[1]))
    assert db.session.query(Reservation).one().language_code == "en"


# --- confirmation page and cancelling -------------------------------------------------------


def test_the_confirmation_page_shows_the_booking_and_the_status(client, tables):
    booking = hold_table(tables[2])
    html = client.get(f"/fa/reservation/{booking.public_token}").get_data(as_text=True)
    assert "تأیید شد" in html and "۱۹:۰۰" in html and "۳" in html


def test_an_unknown_token_is_not_found(client, tables):
    assert client.get("/fa/reservation/nope").status_code == 404
    assert client.post("/fa/reservation/nope/cancel").status_code == 404


def test_a_guest_can_cancel_and_the_table_is_free_again(client, tables):
    booking = hold_table(tables[1])
    page = client.get(f"/fa/reservation/{booking.public_token}").get_data(as_text=True)
    assert "لغو رزرو" in page
    response = client.post(f"/fa/reservation/{booking.public_token}/cancel")
    assert response.status_code == 302
    db.session.refresh(booking)
    assert booking.status is ReservationStatus.CANCELLED
    page = client.get(f"/fa/reservation/{booking.public_token}").get_data(as_text=True)
    assert "لغو شد" in page and "لغو رزرو" not in page
    html = client.get(f"/fa/reserve?date={TOMORROW}&time=19:00").get_data(as_text=True)
    assert 'data-state="busy"' not in html
