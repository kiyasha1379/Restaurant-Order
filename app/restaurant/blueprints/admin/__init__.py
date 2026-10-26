"""The admin panel under /admin. It has no language prefix; staff choose the panel language."""

from flask import Blueprint

admin_blueprint = Blueprint("admin", __name__, url_prefix="/admin")

# Importing the route modules registers their routes on the blueprint.
from restaurant.blueprints.admin import (  # noqa: E402,F401
    auth_routes,
    builders_routes,
    context,
    customers_routes,
    dashboard_routes,
    languages_routes,
    menu_routes,
    orders_routes,
    reservations_routes,
    settings_routes,
    site_routes,
    users_routes,
)
