"""Shared test fixtures: a fresh app and in-memory database for every test."""

from collections.abc import Iterator

import pytest
from flask import Flask, g
from flask.testing import FlaskClient

from restaurant import create_app
from restaurant.constants import TextDirection
from restaurant.extensions import db
from restaurant.models import Language


def add_two_languages() -> None:
    """Insert Persian (default) and English, as the migration does."""
    db.session.add_all(
        [
            Language(code="fa", name="فارسی", direction=TextDirection.RTL, is_default=True),
            Language(code="en", name="English", direction=TextDirection.LTR, is_default=False),
        ]
    )
    db.session.commit()


def forget_signed_in_user_between_requests(application: Flask) -> None:
    """Make every test request start without a cached user.

    The fixtures keep one app context open for the whole test, so `flask.g` (where
    Flask-Login caches the user) would otherwise leak from one client to the next.
    A real server gives each request its own context, so production needs no such hook.
    """

    @application.before_request
    def forget_user() -> None:
        g.pop("_login_user", None)


@pytest.fixture
def app(tmp_path) -> Iterator[Flask]:
    """An app on an empty in-memory database with the two languages present.

    Uploaded photos go to a temporary folder, never into the project.
    """
    application = create_app("test", {"UPLOAD_FOLDER": tmp_path / "uploads"})
    forget_signed_in_user_between_requests(application)
    with application.app_context():
        db.create_all()
        add_two_languages()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """A test client for the app above."""
    return app.test_client()
