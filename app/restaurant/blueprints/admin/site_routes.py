"""The site appearance section: brand, backgrounds, home sections and home texts."""

from flask import flash, redirect, render_template, request, url_for
from werkzeug.wrappers import Response

from restaurant.blueprints.admin import admin_blueprint
from restaurant.blueprints.admin.guards import permission_required
from restaurant.constants import AccessLevel, PermissionKey
from restaurant.extensions import db
from restaurant.forms.admin_site_forms import (
    BackgroundForm,
    BrandForm,
    HomeTextsForm,
    SectionsForm,
)
from restaurant.language_context import get_translator
from restaurant.media import InvalidImageError, InvalidVideoError
from restaurant.service_factory import (
    make_logo_storage,
    make_poster_storage,
    make_site_appearance_service,
    make_site_settings_service,
    make_video_storage,
)
from restaurant.services import InvalidSettingError, SiteAppearanceError

SITE = PermissionKey.SITE
EDIT = AccessLevel.EDIT
BRAND_PROBLEMS = {
    ("brand_name", "length"): "admin.site.error.brand_name",
    ("accent_color", "format"): "admin.site.error.accent_color",
}


# General: brand name, logo and accent colour -------------------------------------------


def _render_brand(form: BrandForm, status: int = 200) -> tuple[str, int]:
    """Draw the general page with the stored logo beside the form."""
    logo = make_site_settings_service().get_logo_path()
    return render_template("admin/site/general.html", form=form, logo=logo), status


@admin_blueprint.get("/site")
@permission_required(SITE)
def site() -> tuple[str, int]:
    """Show the brand name, logo and accent colour."""
    form = BrandForm()
    form.fill(make_site_settings_service().get_site_look())
    return _render_brand(form)


@admin_blueprint.post("/site")
@permission_required(SITE, EDIT)
def site_save() -> tuple[str, int] | Response:
    """Store the brand name, the accent colour and an uploaded or removed logo."""
    translate = get_translator()
    form = BrandForm()
    settings = make_site_settings_service()
    if not form.validate_on_submit():
        return _render_brand(form, 422)

    storage = make_logo_storage()
    new_logo = None
    upload = form.logo.data
    if upload is not None and getattr(upload, "filename", ""):
        try:
            new_logo = storage.save(upload.stream)
        except InvalidImageError as error:
            form.logo.errors = [translate(f"admin.menu.photo.error.{error.problem.value}")]
            return _render_brand(form, 422)

    old_logo = None
    try:
        settings.set_brand(form.brand_name.data or "", form.chosen_color())
        if new_logo or form.remove_logo.data:
            old_logo = settings.get_logo_path()
            settings.set_logo_path(new_logo)
        db.session.commit()
    except InvalidSettingError as problem:
        db.session.rollback()
        storage.delete(new_logo)
        target = form.brand_name if problem.field == "brand_name" else form.accent_color
        target.errors = [translate(BRAND_PROBLEMS[(problem.field, problem.problem)])]
        return _render_brand(form, 422)
    storage.delete(old_logo)
    flash(translate("admin.saved"), "success")
    return redirect(url_for("admin.site"))


# Backgrounds ---------------------------------------------------------------------------


def _render_backgrounds(forms: dict[str, BackgroundForm], status: int = 200):  # noqa: ANN202
    """Draw the backgrounds page; `forms` holds one form per background key."""
    rows = make_site_appearance_service().list_backgrounds()
    return render_template("admin/site/backgrounds.html", rows=rows, forms=forms), status


def _fresh_forms() -> dict[str, BackgroundForm]:
    """Return one form per background, filled with what is stored."""
    forms = {}
    for row in make_site_appearance_service().list_backgrounds():
        form = BackgroundForm(formdata=None)
        form.fill(row)
        forms[row.key] = form
    return forms


@admin_blueprint.get("/site/backgrounds")
@permission_required(SITE)
def site_backgrounds():  # noqa: ANN201
    """List every background with its video, poster and settings."""
    return _render_backgrounds(_fresh_forms())


@admin_blueprint.post("/site/backgrounds/<key>")
@permission_required(SITE, EDIT)
def site_background_save(key: str):  # noqa: ANN201
    """Store one background's settings and any new or removed video and poster."""
    translate = get_translator()
    service = make_site_appearance_service()
    known = {row.key for row in service.list_backgrounds()}
    if key not in known:
        return redirect(url_for("admin.site_backgrounds"))
    forms = _fresh_forms()
    form = BackgroundForm()
    forms[key] = form
    if not form.validate_on_submit():
        return _render_backgrounds(forms, 422)

    posters, videos = make_poster_storage(), make_video_storage()
    new_files: dict[str, str] = {}
    for kind, field, storage in (
        ("poster", form.poster, posters),
        ("video", form.video, videos),
    ):
        upload = field.data
        if upload is None or not getattr(upload, "filename", ""):
            continue
        try:
            new_files[kind] = storage.save(upload.stream)
        except InvalidImageError as error:
            message = translate(f"admin.menu.photo.error.{error.problem.value}")
        except InvalidVideoError as error:
            message = translate(f"admin.site.video.error.{error.problem.value}")
        else:
            continue
        _delete_new(new_files, posters, videos)
        field.errors = [message]
        return _render_backgrounds(forms, 422)

    old_files: list[str | None] = []
    try:
        service.update_background(
            key, form.dim_percent.data / 100, form.is_enabled.data, form.mode()
        )
        for kind, remove in (
            ("poster", form.remove_poster.data),
            ("video", form.remove_video.data),
        ):
            if kind in new_files:
                old_files.append(service.set_background_file(key, kind, new_files[kind]))
            elif remove:
                old_files.append(service.remove_background_file(key, kind))
        db.session.commit()
    except SiteAppearanceError:
        db.session.rollback()
        _delete_new(new_files, posters, videos)
        return _render_backgrounds(forms, 422)
    for old in old_files:
        posters.delete(old)  # Both storages ignore addresses that are not their uploads.
    flash(translate("admin.saved"), "success")
    return redirect(url_for("admin.site_backgrounds") + f"#bg-{key}")


def _delete_new(new_files: dict[str, str], posters, videos) -> None:  # noqa: ANN001
    """Remove files stored for a request that then failed."""
    posters.delete(new_files.get("poster"))
    videos.delete(new_files.get("video"))


# Home page: section order and texts ------------------------------------------------------


@admin_blueprint.get("/site/home")
@permission_required(SITE)
def site_home() -> str:
    """Show the home sections (order and visibility) and the editable home texts."""
    service = make_site_appearance_service()
    return render_template(
        "admin/site/home.html",
        sections=service.home_sections(),
        texts=service.load_home_texts(),
    )


@admin_blueprint.post("/site/home/sections")
@permission_required(SITE, EDIT)
def site_home_sections_save() -> Response:
    """Store the section order and which sections show (an arrow button moves one step)."""
    translate = get_translator()
    form = SectionsForm()
    if form.validate_on_submit():
        order, visible = form.read(request.form.to_dict(flat=False))
        try:
            make_site_appearance_service().save_home_sections(order, visible)
            db.session.commit()
            flash(translate("admin.saved"), "success")
        except SiteAppearanceError:
            db.session.rollback()
            flash(translate("admin.form_error"), "error")
    else:
        flash(translate("admin.form_error"), "error")
    return redirect(url_for("admin.site_home") + "#sections")


@admin_blueprint.post("/site/home/texts")
@permission_required(SITE, EDIT)
def site_home_texts_save() -> Response:
    """Store the edited home texts."""
    translate = get_translator()
    form = HomeTextsForm()
    if form.validate_on_submit():
        make_site_appearance_service().save_home_texts(form.texts(request.form))
        db.session.commit()
        flash(translate("admin.saved"), "success")
    else:
        flash(translate("admin.form_error"), "error")
    return redirect(url_for("admin.site_home") + "#texts")
