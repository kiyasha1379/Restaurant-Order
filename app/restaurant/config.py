"""Application configuration: Dev, Demo and Test (technical plan, section 11)."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INSTANCE_DIR = PROJECT_ROOT / "instance"
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"
DEFAULT_SECRET_KEY = "dev-only-secret-change-me"


class BaseConfig:
    """Settings shared by every configuration."""

    DEBUG = False
    TESTING = False
    # When on, a "demo version" bar is shown on every page and no real
    # external service (bank, SMS, e-mail) is ever contacted.
    DEMO_MODE = False
    SECRET_KEY = os.environ.get("SECRET_KEY", DEFAULT_SECRET_KEY)
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{INSTANCE_DIR / 'restaurant.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_LEVEL = "INFO"
    LOG_TO_FILE = True
    # Uploaded media (backgrounds, dish photos) is kept inside static/ so
    # it is served like any other asset.
    UPLOAD_FOLDER = PROJECT_ROOT / "restaurant" / "static" / "uploads"
    MAX_CONTENT_LENGTH = 13 * 1024 * 1024
    # Staff sessions: the cookie is not readable by scripts and not sent from other sites.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Limits for the sign-in form (per visitor address).
    RATELIMIT_STORAGE_URI = "memory://"
    LOGIN_RATE_LIMIT = "10 per minute"
    CONTACT_RATE_LIMIT = "5 per minute"
    # The class that handles online payments. "mock" is a test page; empty switches online
    # payment off. A real gateway is added in `services/payment_gateway.py`.
    PAYMENT_GATEWAY = "mock"
    # Demo mode (and the tests) accept this code instead of sending an SMS.
    DEMO_VERIFICATION_CODE = "12345"
    # Live order status: how often the stream looks at the database, and how long one stream lives.
    ORDER_STREAM_POLL_SECONDS = 2
    ORDER_STREAM_MAX_SECONDS = 600


class DevConfig(BaseConfig):
    """Local development: debug pages and verbose logs."""

    DEBUG = True
    LOG_LEVEL = "DEBUG"


class DemoConfig(BaseConfig):
    """Demonstration build: demo bar on, sample data allowed."""

    DEMO_MODE = True


class TestConfig(BaseConfig):
    """Automated tests: in-memory database, no log files, no CSRF noise."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    LOG_TO_FILE = False
    LOG_LEVEL = "WARNING"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    ORDER_STREAM_POLL_SECONDS = 0
    ORDER_STREAM_MAX_SECONDS = 0
    SECRET_KEY = "test-secret"


CONFIG_BY_NAME: dict[str, type[BaseConfig]] = {
    "dev": DevConfig,
    "demo": DemoConfig,
    "test": TestConfig,
}


def resolve_config(name: str | None = None) -> type[BaseConfig]:
    """Return the configuration class for `name` (or for the APP_CONFIG variable)."""
    config_name = (name or os.environ.get("APP_CONFIG", "dev")).lower()
    try:
        return CONFIG_BY_NAME[config_name]
    except KeyError as error:
        known_names = ", ".join(sorted(CONFIG_BY_NAME))
        raise ValueError(
            f"Unknown configuration '{config_name}'. Use one of: {known_names}"
        ) from error
