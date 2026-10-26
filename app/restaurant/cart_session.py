"""Keeps the raw cart in the visitor's Flask session (a signed cookie)."""

import json

from flask import session
from sqlalchemy.orm import Session

from restaurant.models import User

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


class AccountCartStorage:
    """CartStorage for a signed-in customer: the session and the account both keep the cart.

    The account copy lets the cart follow the customer to another device. The session stays
    the working copy, so a cart read never touches the database.
    """

    def __init__(self, inner: SessionCartStorage, user: User, db_session: Session) -> None:
        """Keep the session storage, the customer and the database session."""
        self._inner = inner
        self._user = user
        self._db_session = db_session

    def load(self) -> list[dict]:
        """Return the lines of the session cart."""
        return self._inner.load()

    def save(self, raw_lines: list[dict]) -> None:
        """Replace the session cart and the copy saved with the account."""
        self._inner.save(raw_lines)
        self._user.saved_cart = json.dumps(raw_lines)
        self._db_session.commit()

    @staticmethod
    def read_saved(user: User) -> list[dict]:
        """Return the cart saved with the account (an empty list when there is none)."""
        try:
            saved = json.loads(user.saved_cart or "[]")
        except ValueError:
            return []
        return saved if isinstance(saved, list) else []
