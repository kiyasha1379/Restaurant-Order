"""Time helpers: the database stores Gregorian ISO times in Asia/Tehran."""

from datetime import datetime
from zoneinfo import ZoneInfo

from restaurant.constants import TIMEZONE_NAME

TEHRAN_TIMEZONE = ZoneInfo(TIMEZONE_NAME)


def now_tehran() -> datetime:
    """Return the current time in Tehran as a naive datetime.

    Iran has no daylight saving time, so a naive local value is unambiguous;
    keeping it naive matches how SQLite stores datetimes.
    """
    return datetime.now(TEHRAN_TIMEZONE).replace(tzinfo=None)
