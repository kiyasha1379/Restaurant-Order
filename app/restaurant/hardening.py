"""Production safety: refuse unsafe settings, trust the proxy, add security headers."""

from flask import Flask, Response
from werkzeug.middleware.proxy_fix import ProxyFix

from restaurant.config import DEFAULT_SECRET_KEY
from restaurant.models.payment import MOCK_GATEWAY_NAME


class UnsafeConfigurationError(RuntimeError):
    """The settings are not safe for a real installation; the message says what to change."""


def check_production_settings(app: Flask) -> None:
    """Stop the start-up when a production installation has a known-weak setting."""
    key = app.config["SECRET_KEY"]
    if not key or key == DEFAULT_SECRET_KEY or len(key) < 32:
        raise UnsafeConfigurationError(
            "Set the SECRET_KEY environment variable to a random value of 32+ characters "
            '(python -c "import secrets; print(secrets.token_hex(32))").'
        )
    if app.config["PAYMENT_GATEWAY"] == MOCK_GATEWAY_NAME:
        raise UnsafeConfigurationError(
            "PAYMENT_GATEWAY=mock is a test page that never takes money; leave it empty "
            "or configure a real gateway."
        )
    if app.config["DEMO_MODE"]:
        raise UnsafeConfigurationError("DEMO_MODE must be off on a real installation.")


def trust_proxy(app: Flask) -> None:
    """Read the visitor address, scheme and host from the reverse proxy's headers."""
    hops = app.config["PROXY_HOPS"]
    if hops > 0:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops, x_host=hops)


def add_security_headers(app: Flask) -> None:
    """Send the basic protective headers on every response."""

    @app.after_request
    def protect(response: Response) -> Response:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        seconds = app.config["HSTS_SECONDS"]
        if seconds:
            response.headers.setdefault("Strict-Transport-Security", f"max-age={seconds}")
        return response
