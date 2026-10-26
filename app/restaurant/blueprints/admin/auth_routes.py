"""Sign in, sign out and the panel language."""

from flask import current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user
from werkzeug.wrappers import Response

from restaurant.blueprints.admin import admin_blueprint
from restaurant.blueprints.admin.guards import (
    current_profile,
    first_allowed_section,
    is_safe_admin_path,
)
from restaurant.extensions import db, limiter
from restaurant.forms.admin_login_form import LoginForm
from restaurant.language_context import get_translator
from restaurant.service_factory import make_auth_service, make_language_service
from restaurant.services import LoginOutcome

ADMIN_LANGUAGE_SESSION_KEY = "admin_language"
FAILURE_TEXT_KEYS = {
    LoginOutcome.INVALID: "admin.login.error.invalid",
    LoginOutcome.BLOCKED: "admin.login.error.blocked",
    LoginOutcome.NO_ACCESS: "admin.login.error.no_access",
}


def landing_url() -> str:
    """Return the first page the signed-in user may open."""
    section = first_allowed_section(current_profile())
    return url_for(section.endpoint) if section else url_for("admin.login")


@admin_blueprint.get("/")
def index() -> Response:
    """Send staff to their first section (or to the sign-in page)."""
    return redirect(landing_url())


def _login_limit() -> str:
    """Read the sign-in rate limit from the configuration, so tests and servers can change it."""
    return current_app.config["LOGIN_RATE_LIMIT"]


@admin_blueprint.route("/login", methods=["GET", "POST"])
@limiter.limit(_login_limit, methods=["POST"])
def login() -> Response | str:
    """Show the sign-in form and sign the user in when the credentials are right."""
    if current_user.is_authenticated and current_profile().has_admin_access:
        return redirect(landing_url())
    form = LoginForm()
    failure = None
    if form.validate_on_submit():
        result = make_auth_service().authenticate(form.email.data, form.password.data)
        if result.outcome is LoginOutcome.OK:
            login_user(result.user)
            db.session.commit()
            target = request.args.get("next")
            return redirect(target if is_safe_admin_path(target) else landing_url())
        failure = get_translator()(FAILURE_TEXT_KEYS[result.outcome])
    return render_template("admin/login.html", form=form, failure=failure)


@admin_blueprint.post("/logout")
def logout() -> Response:
    """Sign the user out."""
    logout_user()
    flash(get_translator()("admin.login.signed_out"), "info")
    return redirect(url_for("admin.login"))


@admin_blueprint.get("/language/<code>")
def set_language(code: str) -> Response:
    """Remember the panel language for this browser and go back to where the user was."""
    if make_language_service().get_language(code) is not None:
        session[ADMIN_LANGUAGE_SESSION_KEY] = code
    target = request.args.get("next")
    return redirect(target if is_safe_admin_path(target) else url_for("admin.index"))
