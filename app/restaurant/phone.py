"""Iranian mobile numbers: one place that cleans and checks them."""

import re

from restaurant.formatting import to_latin_digits

_MOBILE_PATTERN = re.compile(r"^09\d{9}$")
_SEPARATORS = re.compile(r"[\s\-()]")


def normalize_mobile(raw_number: str) -> str | None:
    """Return the number as 09xxxxxxxxx, or None when it is not an Iranian mobile number.

    Accepts Persian digits, spaces, dashes and the +98 / 0098 / 98 prefixes.
    """
    number = _SEPARATORS.sub("", to_latin_digits(raw_number))
    for prefix in ("+98", "0098", "98"):
        if number.startswith(prefix) and not number.startswith("09"):
            number = "0" + number[len(prefix) :]
            break
    return number if _MOBILE_PATTERN.match(number) else None
