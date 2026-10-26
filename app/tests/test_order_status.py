"""The order state class: which status may follow which."""

import pytest

from restaurant.constants import FulfillmentType, OrderStatus
from restaurant.services import OrderStatusMachine

TAKEAWAY, DELIVERY = FulfillmentType.TAKEAWAY, FulfillmentType.DELIVERY


def walk(fulfillment):
    status, path = OrderStatus.PLACED, [OrderStatus.PLACED]
    while (status := OrderStatusMachine.forward_step(status, fulfillment)) is not None:
        path.append(status)
    return path


def test_takeaway_is_handed_over_when_ready():
    assert walk(TAKEAWAY) == [
        OrderStatus.PLACED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
        OrderStatus.COMPLETED,
    ]


def test_delivery_goes_out_before_it_completes():
    assert OrderStatus.OUT_FOR_DELIVERY in walk(DELIVERY)
    assert walk(DELIVERY)[-1] is OrderStatus.COMPLETED


def test_timeline_matches_the_normal_path():
    assert OrderStatusMachine.timeline(TAKEAWAY) == walk(TAKEAWAY)
    assert OrderStatusMachine.timeline(DELIVERY) == walk(DELIVERY)


@pytest.mark.parametrize("status", [OrderStatus.PLACED, OrderStatus.PREPARING, OrderStatus.READY])
def test_an_open_order_can_be_cancelled(status):
    assert OrderStatusMachine.can_move(status, OrderStatus.CANCELLED, TAKEAWAY)


@pytest.mark.parametrize("final", [OrderStatus.COMPLETED, OrderStatus.CANCELLED])
def test_final_orders_cannot_move(final):
    assert OrderStatusMachine.is_final(final)
    assert OrderStatusMachine.allowed_next(final, DELIVERY) == []


def test_steps_cannot_be_skipped_or_reversed():
    assert not OrderStatusMachine.can_move(OrderStatus.PLACED, OrderStatus.READY, TAKEAWAY)
    assert not OrderStatusMachine.can_move(OrderStatus.READY, OrderStatus.PREPARING, TAKEAWAY)


def test_a_takeaway_order_never_goes_out_for_delivery():
    assert not OrderStatusMachine.can_move(
        OrderStatus.READY, OrderStatus.OUT_FOR_DELIVERY, TAKEAWAY
    )
    assert not OrderStatusMachine.can_move(OrderStatus.READY, OrderStatus.COMPLETED, DELIVERY)
