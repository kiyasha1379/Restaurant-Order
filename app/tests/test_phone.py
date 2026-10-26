"""Mobile number cleaning."""

import pytest

from restaurant.phone import normalize_mobile


@pytest.mark.parametrize(
    "raw",
    [
        "09123456789",
        "۰۹۱۲۳۴۵۶۷۸۹",
        "0912 345 6789",
        "0912-345-6789",
        "+989123456789",
        "00989123456789",
        "989123456789",
    ],
)
def test_valid_numbers_become_the_plain_form(raw):
    assert normalize_mobile(raw) == "09123456789"


@pytest.mark.parametrize(
    "raw", ["", "0912345678", "091234567890", "02112345678", "abcdefghijk", "9123456789"]
)
def test_invalid_numbers_are_rejected(raw):
    assert normalize_mobile(raw) is None
