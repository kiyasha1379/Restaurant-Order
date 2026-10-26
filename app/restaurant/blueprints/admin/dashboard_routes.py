"""The dashboard: today's numbers and the things that need attention."""

from flask import render_template

from restaurant.blueprints.admin import admin_blueprint
from restaurant.blueprints.admin.guards import current_profile, permission_required
from restaurant.constants import OrderStatus, PermissionKey
from restaurant.service_factory import make_dashboard_service


@admin_blueprint.get("/dashboard")
@permission_required(PermissionKey.DASH)
def dashboard() -> str:
    """Show today's orders, sales (only with the 'money' permission), busy hours and alerts."""
    data = make_dashboard_service().today()
    return render_template(
        "admin/dashboard.html",
        data=data,
        show_money=current_profile().can_see_money,
        statuses=[s for s in OrderStatus if s is not OrderStatus.CANCELLED],
    )
