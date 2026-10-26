"""The payment gateway interface and the test gateway (the Strategy pattern).

A gateway does two things (technical plan, section 8): `start()` registers a payment
and says where to send the customer, and `verify()` asks the gateway what happened
when the customer comes back. An order becomes paid only after `verify()` says so.
A real bank gateway is one more class behind this interface plus one line in
`create_gateway()`; nothing else changes.
"""

import secrets
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from restaurant.models.payment import MOCK_GATEWAY_NAME, MOCK_TRANSACTION_PREFIX


class GatewayError(RuntimeError):
    """The gateway could not be reached or refused the request."""


class UnknownGatewayError(ValueError):
    """The `PAYMENT_GATEWAY` setting names a gateway that does not exist."""


@dataclass(frozen=True)
class StartRequest:
    """What the gateway needs to register one payment."""

    order_number: int
    amount: int
    callback_url: str
    language_code: str


@dataclass(frozen=True)
class StartResult:
    """The gateway's reference for the payment and the address to send the customer to."""

    authority: str
    redirect_url: str


class GatewayOutcome(StrEnum):
    """What the gateway says happened."""

    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class VerifyResult:
    """The gateway's answer: the outcome, its transaction id and the amount it charged."""

    outcome: GatewayOutcome
    transaction_id: str = ""
    amount: int = 0


class PaymentGateway(ABC):
    """What every gateway can do. Implementations hold no order data."""

    name: ClassVar[str]

    @abstractmethod
    def start(self, request: StartRequest) -> StartResult:
        """Register a payment and return its reference and the page to send the customer to."""

    @abstractmethod
    def authority_from(self, params: Mapping[str, str]) -> str:
        """Read the payment reference out of the parameters the gateway sends back."""

    @abstractmethod
    def verify(self, authority: str, amount: int, params: Mapping[str, str]) -> VerifyResult:
        """Ask the gateway what happened to the payment `authority` of `amount` tomans."""


class MockGateway(PaymentGateway):
    """A stand-in for a bank: a test page, no card form, no money.

    The test page sends the customer back with `status=ok`, `failed` or `cancel`,
    exactly where a real gateway would send its own answer; `verify()` turns that
    into the same result a real gateway would return.
    """

    name = MOCK_GATEWAY_NAME
    AUTHORITY_PREFIX = "MOCKA-"
    STATUS_OK = "ok"
    STATUS_CANCEL = "cancel"

    def __init__(self, page_url: Callable[[str, str], str]) -> None:
        """Receive a function that builds the test page address from (authority, language)."""
        self._page_url = page_url

    def start(self, request: StartRequest) -> StartResult:
        """Create a reference and point at the test gateway page."""
        authority = f"{self.AUTHORITY_PREFIX}{secrets.token_hex(10)}"
        return StartResult(authority, self._page_url(authority, request.language_code))

    def authority_from(self, params: Mapping[str, str]) -> str:
        """Return the `authority` parameter."""
        return params.get("authority", "")

    def verify(self, authority: str, amount: int, params: Mapping[str, str]) -> VerifyResult:
        """Turn the test page's answer into a gateway result."""
        answer = params.get("status", "")
        if answer == self.STATUS_OK:
            transaction_id = f"{MOCK_TRANSACTION_PREFIX}{secrets.token_hex(5).upper()}"
            return VerifyResult(GatewayOutcome.PAID, transaction_id, amount)
        if answer == self.STATUS_CANCEL:
            return VerifyResult(GatewayOutcome.CANCELLED)
        return VerifyResult(GatewayOutcome.FAILED)


def create_gateway(name: str, mock_page_url: Callable[[str, str], str]) -> PaymentGateway:
    """Build the gateway named by the `PAYMENT_GATEWAY` setting (the Factory pattern)."""
    if name == MockGateway.name:
        return MockGateway(mock_page_url)
    raise UnknownGatewayError(f"Unknown payment gateway: {name!r}")
