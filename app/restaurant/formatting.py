"""Number, price and date formatting for both site languages.

Dates are stored as Gregorian values but always shown in the Jalali calendar
(technical plan, section 8). Month lengths and leap years come from
`jdatetime`; nothing is calculated by hand here.
"""

from datetime import date, datetime, time

import jdatetime

from restaurant.constants import LANGUAGE_CODE_PERSIAN

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
LATIN_DIGITS = "0123456789"
PERSIAN_THOUSANDS_SEPARATOR = "٬"

_TO_PERSIAN_DIGITS = str.maketrans(LATIN_DIGITS, PERSIAN_DIGITS)
_TO_LATIN_DIGITS = str.maketrans(PERSIAN_DIGITS + ARABIC_INDIC_DIGITS, LATIN_DIGITS * 2)

CURRENCY_NAME = {"fa": "تومان", "en": "Toman"}

JALALI_MONTH_NAMES = {
    "fa": (
        "فروردین",
        "اردیبهشت",
        "خرداد",
        "تیر",
        "مرداد",
        "شهریور",
        "مهر",
        "آبان",
        "آذر",
        "دی",
        "بهمن",
        "اسفند",
    ),
    "en": (
        "Farvardin",
        "Ordibehesht",
        "Khordad",
        "Tir",
        "Mordad",
        "Shahrivar",
        "Mehr",
        "Aban",
        "Azar",
        "Dey",
        "Bahman",
        "Esfand",
    ),
}

# Indexed by `date.weekday()`: Monday is 0.
WEEKDAY_NAMES = {
    "fa": ("دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"),
    "en": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
}


def to_persian_digits(text: str) -> str:
    """Replace Latin digits with Persian ones."""
    return str(text).translate(_TO_PERSIAN_DIGITS)


def to_latin_digits(text: str) -> str:
    """Replace Persian and Arabic-Indic digits with Latin ones (for reading user input)."""
    return str(text).translate(_TO_LATIN_DIGITS)


def localize_digits(text: str, language_code: str) -> str:
    """Show digits the way the language writes them: Persian digits only for Persian."""
    return to_persian_digits(text) if language_code == LANGUAGE_CODE_PERSIAN else str(text)


def format_number(value: int, language_code: str) -> str:
    """Format a whole number with thousands separators: ۱۲۰٬۰۰۰ or 120,000."""
    grouped = f"{value:,}"
    if language_code == LANGUAGE_CODE_PERSIAN:
        return to_persian_digits(grouped).replace(",", PERSIAN_THOUSANDS_SEPARATOR)
    return grouped


def format_price(amount_toman: int, language_code: str) -> str:
    """Format a price in whole tomans: ۱۲۰٬۰۰۰ تومان or 120,000 Toman."""
    currency = CURRENCY_NAME.get(language_code, CURRENCY_NAME["en"])
    return f"{format_number(amount_toman, language_code)} {currency}"


def to_jalali(value: date | datetime) -> jdatetime.date:
    """Convert a Gregorian date (or the date part of a datetime) to Jalali."""
    gregorian_date = value.date() if isinstance(value, datetime) else value
    return jdatetime.date.fromgregorian(date=gregorian_date)


def format_jalali_date(
    value: date | datetime, language_code: str, *, with_weekday: bool = False
) -> str:
    """Format a date as '۴ آبان ۱۴۰۵' or '4 Aban 1405', optionally with the weekday."""
    gregorian_date = value.date() if isinstance(value, datetime) else value
    jalali_date = to_jalali(gregorian_date)
    month_names = JALALI_MONTH_NAMES.get(language_code, JALALI_MONTH_NAMES["en"])
    text = f"{jalali_date.day} {month_names[jalali_date.month - 1]} {jalali_date.year}"
    if with_weekday:
        weekday_names = WEEKDAY_NAMES.get(language_code, WEEKDAY_NAMES["en"])
        separator = "،" if language_code == LANGUAGE_CODE_PERSIAN else ","
        text = f"{weekday_names[gregorian_date.weekday()]}{separator} {text}"
    return localize_digits(text, language_code)


def format_jalali_numeric(value: date | datetime, language_code: str) -> str:
    """Format a date as 1405/08/04 (with Persian digits in Persian)."""
    jalali_date = to_jalali(value)
    text = f"{jalali_date.year}/{jalali_date.month:02d}/{jalali_date.day:02d}"
    return localize_digits(text, language_code)


def format_time(value: datetime | time, language_code: str) -> str:
    """Format a time of day as 14:30."""
    return localize_digits(value.strftime("%H:%M"), language_code)


def format_jalali_datetime(value: datetime, language_code: str) -> str:
    """Format a date and time: '۴ آبان ۱۴۰۵، ۱۴:۳۰'."""
    return f"{format_jalali_date(value, language_code)}، {format_time(value, language_code)}"
