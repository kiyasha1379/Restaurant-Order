"""Keeps the raw cart in the visitor's Flask session (a signed cookie)."""

from flask import session

CART_SESSION_KEY = "cart"


class SessionCartStorage:
    """CartStorage backed by `flask.session`."""

    def load(self) -> list[dict]:
        """Return the stored lines, or an empty list when there are none."""
        stored = session.get(CART_SESSION_KEY)
        return stored if isinstance(stored, list) else []

    def save(self, raw_lines: list[dict]) -> None:
        """Replace the stored lines."""
        session[CART_SESSION_KEY] = raw_lines
        session.modified = True
