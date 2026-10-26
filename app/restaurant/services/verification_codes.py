"""Where verification codes come from. Demo mode uses a fixed code and sends nothing."""

import logging
import secrets
from typing import Protocol

CODE_LENGTH = 5

_logger = logging.getLogger(__name__)


class CodeIssuer(Protocol):
    """Makes a code for a phone number and delivers it (a real SMS provider fits here later)."""

    def issue(self, phone: str) -> str:
        """Return the code that the customer must type."""


class FixedCodeIssuer:
    """Demo mode: every code is the same and nothing is sent anywhere."""

    def __init__(self, code: str) -> None:
        """Remember the fixed code."""
        self._code = code

    def issue(self, phone: str) -> str:  # noqa: ARG002 - the demo code ignores the phone
        """Return the fixed code."""
        return self._code


class LoggedCodeIssuer:
    """No SMS provider is connected yet, so a random code is written to the server log."""

    def issue(self, phone: str) -> str:
        """Return a random code and log it as the "message" that would have been sent."""
        code = "".join(secrets.choice("0123456789") for _ in range(CODE_LENGTH))
        _logger.warning(
            "Verification code for %s is %s (no SMS provider is connected)", phone, code
        )
        return code
