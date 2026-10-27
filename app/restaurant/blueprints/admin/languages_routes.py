"""The languages section: translation status, language switches and interface texts."""

from flask import flash, redirect, render_template, request, url_for
from werkzeug.wrappers import Response

from restaurant.blueprints.admin import admin_blueprint
from restaurant.blueprints.admin.guards import permission_required, safe_admin_target
from restaurant.constants import SUPPORTED_LANGUAGE_CODES, AccessLevel, PermissionKey
from restaurant.extensions import db
from restaurant.language_context import get_translator
from restaurant.service_factory import make_language_admin_service
from restaurant.services import LanguageAdminError

LANGUAGES = PermissionKey.LANGUAGES
EDIT = AccessLevel.EDIT
MISSING_FILTERS = frozenset(SUPPORTED_LANGUAGE_CODES)


@admin_blueprint.get("/languages")
@permission_required(LANGUAGES)
def languages() -> str:
    """Show both languages with their switches and how complete their translations are."""
    service = make_language_admin_service()
    return render_template(
        "admin/languages/overview.html",
        statuses=service.list_status(),
        missing_english=service.missing_keys("en"),
    )


@admin_blueprint.post("/languages/settings")
@permission_required(LANGUAGES, EDIT)
def languages_save_settings() -> Response:
    """Switch English on or off and choose the default language."""
    translate = get_translator()
    try:
        make_language_admin_service().update_settings(
            english_enabled=request.form.get("english_enabled") == "1",
            default_code=request.form.get("default_code", ""),
        )
        db.session.commit()
    except LanguageAdminError:
        db.session.rollback()
        flash(translate("admin.languages.error.default"), "error")
    else:
        flash(translate("admin.saved"), "success")
    return redirect(url_for("admin.languages"))


@admin_blueprint.get("/languages/texts")
@permission_required(LANGUAGES)
def language_texts() -> str:
    """List the interface texts in both languages, ready to edit."""
    query = request.args.get("q", "").strip()
    missing = request.args.get("missing")
    missing = missing if missing in MISSING_FILTERS else None
    page = make_language_admin_service().list_texts(
        query, missing, request.args.get("page", 1, type=int)
    )
    return render_template(
        "admin/languages/texts.html",
        page=page,
        query=query,
        missing=missing,
        return_to=request.full_path.rstrip("?"),
    )


@admin_blueprint.post("/languages/texts")
@permission_required(LANGUAGES, EDIT)
def language_texts_save() -> Response:
    """Save the texts shown on one page of the editor."""
    entries = {
        key: {code: request.form.get(f"text:{code}:{key}", "") for code in SUPPORTED_LANGUAGE_CODES}
        for key in request.form.getlist("keys")
    }
    changed = make_language_admin_service().save_texts(entries)
    db.session.commit()
    flash(get_translator()("admin.languages.texts_saved", count=changed), "success")
    target = request.form.get("next")
    return redirect(safe_admin_target(target) or url_for("admin.language_texts"))
