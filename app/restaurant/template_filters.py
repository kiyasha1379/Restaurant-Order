"""Jinja filters for numbers, prices and Jalali dates in the active language."""

from datetime import date, datetime

from flask import Flask

from restaurant import formatting
from restaurant.language_context import get_active_language


def _code() -> str:
    """Return the active language code."""
    return get_active_language().code


def number_filter(value: int) -> str:
    """{{ 120000|number }} -> ۱۲۰٬۰۰۰ or 120,000."""
    return formatting.format_number(value, _code())


def price_filter(value: int) -> str:
    """{{ 120000|price }} -> ۱۲۰٬۰۰۰ تومان or 120,000 Toman."""
    return formatting.format_price(value, _code())


def digits_filter(value: object) -> str:
    """{{ "A3"|digits }} -> A۳ in Persian, A3 in English (labels that may hold letters)."""
    return formatting.localize_digits(str(value), _code())


def jdate_filter(value: date | datetime, with_weekday: bool = False) -> str:
    """{{ day|jdate }} -> ۴ آبان ۱۴۰۵ (or with the weekday in front)."""
    return formatting.format_jalali_date(value, _code(), with_weekday=with_weekday)


def jdate_numeric_filter(value: date | datetime) -> str:
    """{{ day|jdate_numeric }} -> ۱۴۰۵/۰۸/۰۴."""
    return formatting.format_jalali_numeric(value, _code())


def jtime_filter(value: datetime) -> str:
    """{{ moment|jtime }} -> ۱۴:۳۰."""
    return formatting.format_time(value, _code())


def jdatetime_filter(value: datetime) -> str:
    """{{ moment|jdatetime }} -> ۴ آبان ۱۴۰۵، ۱۴:۳۰."""
    return formatting.format_jalali_datetime(value, _code())


def register_template_filters(app: Flask) -> None:
    """Make the filters available in every template."""
    app.add_template_filter(number_filter, "number")
    app.add_template_filter(digits_filter, "digits")
    app.add_template_filter(price_filter, "price")
    app.add_template_filter(jdate_filter, "jdate")
    app.add_template_filter(jdate_numeric_filter, "jdate_numeric")
    app.add_template_filter(jtime_filter, "jtime")
    app.add_template_filter(jdatetime_filter, "jdatetime")
