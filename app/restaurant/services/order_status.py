"""Order statuses and the moves between them (the State pattern, in one class).

A takeaway order is handed over when it is ready; a delivery order goes out
first. Cancelling is possible until the order is completed. An order that waits for
its online payment can only be cancelled: it enters the kitchen's queue through a
verified payment (`OrderService.confirm_payment`), never through a status button.
"""

from restaurant.constants import FulfillmentType, OrderStatus

_FINAL_STATUSES = frozenset({OrderStatus.COMPLETED, OrderStatus.CANCELLED})


class OrderStatusMachine:
    """Knows which status may follow which. It holds no data, so its methods are static."""

    @staticmethod
    def forward_step(status: OrderStatus, fulfillment: FulfillmentType) -> OrderStatus | None:
        """Return the normal next status, or None when the order is finished."""
        is_delivery = fulfillment is FulfillmentType.DELIVERY
        steps = {
            OrderStatus.PLACED: OrderStatus.PREPARING,
            OrderStatus.PREPARING: OrderStatus.READY,
            OrderStatus.READY: (
                OrderStatus.OUT_FOR_DELIVERY if is_delivery else OrderStatus.COMPLETED
            ),
            OrderStatus.OUT_FOR_DELIVERY: OrderStatus.COMPLETED,
        }
        return steps.get(status)

    @classmethod
    def allowed_next(cls, status: OrderStatus, fulfillment: FulfillmentType) -> list[OrderStatus]:
        """Return every status the order may move to now, forward step first."""
        if status in _FINAL_STATUSES:
            return []
        forward = cls.forward_step(status, fulfillment)
        return [forward, OrderStatus.CANCELLED] if forward else [OrderStatus.CANCELLED]

    @classmethod
    def can_move(
        cls, current: OrderStatus, target: OrderStatus, fulfillment: FulfillmentType
    ) -> bool:
        """Return True when the move is allowed."""
        return target in cls.allowed_next(current, fulfillment)

    @staticmethod
    def is_final(status: OrderStatus) -> bool:
        """Return True when nothing can happen to the order any more."""
        return status in _FINAL_STATUSES

    @staticmethod
    def timeline(fulfillment: FulfillmentType) -> list[OrderStatus]:
        """Return the statuses a normal order passes through, for the tracking page."""
        steps = [OrderStatus.PLACED, OrderStatus.PREPARING, OrderStatus.READY]
        if fulfillment is FulfillmentType.DELIVERY:
            steps.append(OrderStatus.OUT_FOR_DELIVERY)
        return [*steps, OrderStatus.COMPLETED]
