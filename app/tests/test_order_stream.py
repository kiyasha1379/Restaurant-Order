"""The live status stream, run without waiting."""

import json

from restaurant.constants import OrderStatus
from restaurant.order_stream import KEEPALIVE_COMMENT, OrderStatusStream


def make_stream(statuses, max_seconds=100, final=lambda s: s is OrderStatus.COMPLETED):
    readings = iter(statuses)
    ticks = iter(range(1000))
    return OrderStatusStream(
        read_status=lambda: next(readings),
        describe=lambda status: {"status": status.value},
        is_final=final,
        poll_seconds=1,
        max_seconds=max_seconds,
        sleep=lambda seconds: None,
        clock=lambda: next(ticks),
    )


def payloads(events):
    return [json.loads(e.split("data: ")[1]) for e in events if e.startswith("event: status")]


def test_first_event_is_the_current_status():
    events = list(make_stream([OrderStatus.COMPLETED]).events())
    assert payloads(events) == [{"status": "completed"}]


def test_only_changes_are_sent_and_the_rest_are_keepalives():
    statuses = [
        OrderStatus.PLACED,
        OrderStatus.PLACED,
        OrderStatus.PREPARING,
        OrderStatus.PREPARING,
        OrderStatus.COMPLETED,
    ]
    events = list(make_stream(statuses).events())
    assert [p["status"] for p in payloads(events)] == ["placed", "preparing", "completed"]
    assert events.count(KEEPALIVE_COMMENT) == 2


def test_stream_ends_when_the_time_limit_passes():
    events = list(make_stream([OrderStatus.PLACED] * 50, max_seconds=5).events())
    assert len(payloads(events)) == 1
    assert len(events) <= 6


def test_event_text_is_valid_server_sent_event_syntax():
    event = next(iter(make_stream([OrderStatus.COMPLETED]).events()))
    assert event.startswith("event: status\ndata: ") and event.endswith("\n\n")
