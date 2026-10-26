"""Error pages shared by the whole site."""

from flask import Flask, render_template
from werkzeug.exceptions import HTTPException


def render_error_page(error: HTTPException) -> tuple[str, int]:
    """Render the page that matches the error's status code."""
    return render_template(f"errors/{error.code}.html"), error.code or 500


def register_error_handlers(app: Flask) -> None:
    """Use our own error pages instead of the framework defaults."""
    for status_code in (400, 403, 404, 413, 429, 500):
        app.register_error_handler(status_code, render_error_page)
