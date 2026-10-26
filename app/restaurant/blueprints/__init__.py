"""Blueprints: HTTP only, no business logic."""

from flask import Flask

from restaurant.blueprints.admin import admin_blueprint
from restaurant.blueprints.api import api_blueprint
from restaurant.blueprints.errors import register_error_handlers
from restaurant.blueprints.language_routing import register_language_routing
from restaurant.blueprints.public import public_blueprint


def register_blueprints(app: Flask) -> None:
    """Attach every blueprint and the error pages to the application."""
    register_language_routing(app)
    app.register_blueprint(public_blueprint)
    app.register_blueprint(api_blueprint)
    app.register_blueprint(admin_blueprint)
    register_error_handlers(app)
