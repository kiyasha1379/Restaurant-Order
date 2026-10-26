"""Per-request setup for admin pages: the panel language, template values and error pages."""

from typing import Any

from flask import render_template, request, session, url_for
from flask_login import current_user

from restaurant.admin_sections import ADMIN_SECTIONS
from restaurant.blueprints.admin import admin_blueprint
from restaurant.blueprints.admin.auth_routes import ADMIN_LANGUAGE_SESSION_KEY
from restaurant.blueprints.admin.guards import current_profile
from restaurant.constants import AccessLevel, PermissionKey
from restaurant.language_context import (
    find_default_language,
    get_active_language,
    set_active_language,
)
from restaurant.service_factory import make_dashboard_service, make_language_service


@admin_blueprint.before_request
def choose_panel_language() -> None:
    """Use the language staff picked (stored in the session), else the default language."""
    code = session.get(ADMIN_LANGUAGE_SESSION_KEY, "")
    language = make_language_service().get_language(code) if code else None
    set_active_language(language or find_default_language())


@admin_blueprint.context_processor
def admin_template_values() -> dict[str, Any]:
    """Give admin templates the access profile, the visible sections and the language links."""
    profile = current_profile()
    sections = [
        {
            "label_key": section.label_key,
            "icon": section.icon,
            "url": url_for(section.endpoint),
            "active": request.path.startswith(url_for(section.endpoint)),
            "permission": section.permission,
        }
        for section in ADMIN_SECTIONS
        if profile.allows(section.permission)
    ]
    return {
        "access": profile,
        "keys": PermissionKey,
        "levels": AccessLevel,
        "sections": sections,
        "staff_user": current_user if current_user.is_authenticated else None,
        "language_links": admin_language_links,
        "waiting_orders_count": waiting_orders_count,
    }


def admin_language_links() -> list[dict[str, str]]:
    """Links that switch the panel to each language (both are always offered)."""
    active = get_active_language().code
    names = {"fa": "فارسی", "en": "English"}
    return [
        {
            "code": code,
            "name": name,
            "url": url_for("admin.set_language", code=code, next=request.path),
        }
        for code, name in names.items()
        if code != active
    ]


@admin_blueprint.errorhandler(403)
def forbidden(_error: Exception) -> tuple[str, int]:
    """Show the 403 page inside the panel."""
    return render_template("admin/forbidden.html"), 403


def waiting_orders_count() -> int:
    """Return how many orders wait for acceptance (the badge beside 'Orders')."""
    return make_dashboard_service().count_waiting_orders()
