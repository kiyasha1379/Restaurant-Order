"""Restaurant website: application factory."""

from typing import Any

from flask import Flask

from restaurant import database, models  # noqa: F401  (register the SQLite hook and every table)
from restaurant.blueprints import register_blueprints
from restaurant.cli import register_commands
from restaurant.config import INSTANCE_DIR, MIGRATIONS_DIR, resolve_config
from restaurant.extensions import csrf, db, limiter, login_manager, migrate
from restaurant.hardening import add_security_headers, check_production_settings, trust_proxy
from restaurant.logging_setup import configure_logging
from restaurant.template_context import register_template_context
from restaurant.template_filters import register_template_filters


def create_app(config_name: str | None = None, overrides: dict[str, Any] | None = None) -> Flask:
    """Build and configure the Flask application.

    `config_name` is 'dev', 'demo', 'prod' or 'test'; when omitted the APP_CONFIG
    environment variable decides (default 'dev'). `overrides` replaces single
    settings afterwards; tests use it to point at a temporary database.
    """
    app = Flask(__name__, instance_path=str(INSTANCE_DIR))
    app.config.from_object(resolve_config(config_name))
    app.config.update(overrides or {})
    if resolve_config(config_name).__name__ == "ProdConfig":
        check_production_settings(app)
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

    configure_logging(app)
    trust_proxy(app)
    add_security_headers(app)

    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db, directory=str(MIGRATIONS_DIR))

    register_template_context(app)
    register_template_filters(app)
    register_blueprints(app)
    register_commands(app)
    return app
