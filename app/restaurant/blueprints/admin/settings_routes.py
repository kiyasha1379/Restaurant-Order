"""The settings section: delivery fee, payment methods, pausing orders and contact details."""

from flask import flash, redirect, render_template, url_for
from werkzeug.wrappers import Response

from restaurant.blueprints.admin import admin_blueprint
from restaurant.blueprints.admin.guards import permission_required
from restaurant.constants import AccessLevel, PermissionKey
from restaurant.extensions import db
from restaurant.forms.admin_settings_forms import SettingsForm
from restaurant.language_context import get_translator
from restaurant.service_factory import make_settings_admin_service
from restaurant.services import InvalidSettingError

SETTINGS = PermissionKey.SETTINGS
EDIT = AccessLevel.EDIT


@admin_blueprint.get("/settings")
@permission_required(SETTINGS)
def settings() -> str:
    """Show the settings form filled with what is stored now."""
    form = SettingsForm()
    form.fill(make_settings_admin_service().load())
    return render_template("admin/settings/settings.html", form=form)


@admin_blueprint.post("/settings")
@permission_required(SETTINGS, EDIT)
def settings_save() -> str | Response:
    """Validate and store the settings; show the form again with messages when it is refused."""
    form = SettingsForm()
    translate = get_translator()
    if not form.validate_on_submit():
        return render_template("admin/settings/settings.html", form=form), 422
    try:
        make_settings_admin_service().save(form.to_data())
    except InvalidSettingError as problem:
        db.session.rollback()
        form.show_problem(problem, translate)
        return render_template("admin/settings/settings.html", form=form), 422
    db.session.commit()
    flash(translate("admin.saved"), "success")
    return redirect(url_for("admin.settings"))
