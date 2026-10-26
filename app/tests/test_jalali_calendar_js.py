"""The browser calendar must agree with the server's jdatetime conversion."""

import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

import jdatetime
import pytest

JS_TEST_DIRECTORY = Path(__file__).parent / "js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")


def run_node(*arguments: str) -> subprocess.CompletedProcess:
    """Run Node.js with the given arguments and fail loudly on a non-zero exit."""
    return subprocess.run(
        ["node", *arguments], capture_output=True, text=True, check=True, timeout=120
    )


def test_javascript_unit_tests_pass():
    result = run_node("--test", str(JS_TEST_DIRECTORY / "jalali-calendar.test.mjs"))
    assert "fail 0" in result.stdout


def test_every_day_from_1990_to_2060_matches_jdatetime():
    pairs = json.loads(run_node(str(JS_TEST_DIRECTORY / "dump_conversions.mjs")).stdout)
    assert len(pairs) > 25000
    mismatches = []
    for gregorian_iso, jalali_key, round_trip_iso in pairs:
        expected = jdatetime.date.fromgregorian(date=date.fromisoformat(gregorian_iso))
        expected_key = f"{expected.year}/{expected.month:02d}/{expected.day:02d}"
        if jalali_key != expected_key or round_trip_iso != gregorian_iso:
            mismatches.append((gregorian_iso, jalali_key, expected_key))
    assert mismatches == []
