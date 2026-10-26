"""Number, price and Jalali date formatting."""

from datetime import date, datetime

import pytest

from restaurant import formatting


def test_digit_conversion_round_trip():
    assert formatting.to_persian_digits("0123456789") == "۰۱۲۳۴۵۶۷۸۹"
    assert formatting.to_latin_digits("۰۹۱۲٣٤٥") == "0912345"


def test_numbers_are_grouped_per_language():
    assert formatting.format_number(1234567, "en") == "1,234,567"
    assert formatting.format_number(1234567, "fa") == "۱٬۲۳۴٬۵۶۷"
    assert formatting.format_number(0, "fa") == "۰"


def test_prices_carry_the_currency_name():
    assert formatting.format_price(120000, "fa") == "۱۲۰٬۰۰۰ تومان"
    assert formatting.format_price(120000, "en") == "120,000 Toman"


@pytest.mark.parametrize(
    ("gregorian", "jalali"),
    [
        (date(2026, 3, 21), "1405/01/01"),
        (date(2025, 3, 21), "1404/01/01"),
        (date(2024, 3, 20), "1403/01/01"),
        (date(2026, 10, 26), "1405/08/04"),
        (date(2025, 3, 20), "1403/12/30"),  # last day of the leap year 1403
    ],
)
def test_jalali_numeric_dates(gregorian, jalali):
    assert formatting.format_jalali_numeric(gregorian, "en") == jalali
    assert formatting.format_jalali_numeric(gregorian, "fa") == formatting.to_persian_digits(jalali)


def test_long_dates_in_both_languages():
    day = date(2026, 10, 26)
    assert formatting.format_jalali_date(day, "fa") == "۴ آبان ۱۴۰۵"
    assert formatting.format_jalali_date(day, "en") == "4 Aban 1405"
    assert formatting.format_jalali_date(day, "fa", with_weekday=True) == "دوشنبه، ۴ آبان ۱۴۰۵"
    assert formatting.format_jalali_date(day, "en", with_weekday=True) == "Monday, 4 Aban 1405"


def test_datetimes_use_their_date_and_time():
    moment = datetime(2026, 10, 26, 9, 5)
    assert formatting.format_jalali_datetime(moment, "fa") == "۴ آبان ۱۴۰۵، ۰۹:۰۵"
    assert formatting.format_time(moment, "en") == "09:05"
