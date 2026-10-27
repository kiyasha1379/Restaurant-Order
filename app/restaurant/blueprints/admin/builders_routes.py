"""Builder management: builders, their steps and the options of each step (with pictures)."""

from flask import abort, flash, redirect, render_template, request, url_for
from werkzeug.wrappers import Response

from restaurant.blueprints.admin import admin_blueprint
from restaurant.blueprints.admin.guards import permission_required, safe_admin_target
from restaurant.constants import AccessLevel, PermissionKey
from restaurant.extensions import db
from restaurant.forms.admin_builder_forms import BuilderForm, OptionForm, StepForm
from restaurant.language_context import get_translator
from restaurant.media import InvalidImageError
from restaurant.models import Builder, BuilderOption, BuilderStep
from restaurant.service_factory import make_builder_admin_service, make_builder_image_storage
from restaurant.services import BuilderAdminError, DuplicateKeyError, InvalidKeyError
from restaurant.services.localized import pick_translation

BUILDERS = PermissionKey.BUILDERS
EDIT = AccessLevel.EDIT
DIRECTIONS = {"up": -1, "down": 1}
# Shapes the pictures understand; the option form offers them as suggestions.
SHAPE_SUGGESTIONS = (
    "ring",
    "square",
    "pebble",
    "thin",
    "stuffed",
    "flat",
    "round",
    "sauce",
    "wavy",
    "ice",
    "cream",
    "other",
)


def text_of(translations, language_code: str, attribute: str, fallback: str) -> str:  # noqa: ANN001
    """Return one text of a row in the panel language (Persian when missing)."""
    row = pick_translation(translations, language_code)
    value = getattr(row, attribute, "") if row else ""
    return value or fallback


def _back_to(default_endpoint: str, **values) -> Response:  # noqa: ANN003 - url_for values
    """Redirect to `next` when it is a panel address, else to the default page."""
    target = request.form.get("next")
    return redirect(safe_admin_target(target) or url_for(default_endpoint, **values))


def _direction() -> int:
    """Read the move direction from the form or answer 400."""
    direction = DIRECTIONS.get(request.form.get("direction", ""))
    if direction is None:
        abort(400)
    return direction


def _key_error_message(error: BuilderAdminError) -> str:
    """Return the translated message for a refused key or setting."""
    translate = get_translator()
    if isinstance(error, DuplicateKeyError):
        return translate("admin.builders.error.key_duplicate")
    if isinstance(error, InvalidKeyError):
        return translate("admin.builders.error.key_invalid")
    return translate("admin.builders.error.appearance")


def _delete_files(paths) -> None:  # noqa: ANN001 - an iterable of stored paths
    """Remove stored pictures after the database change has been committed."""
    storage = make_builder_image_storage()
    for path in paths:
        storage.delete(path)


# --- builders ----------------------------------------------------------


@admin_blueprint.get("/builders")
@permission_required(BUILDERS)
def builders() -> str:
    """List the builders with their order, visibility and the number of steps."""
    return render_template(
        "admin/builders/list.html",
        builders=make_builder_admin_service().list_builders(),
        text_of=text_of,
    )


def _load_builder(builder_id: int) -> Builder:
    """Return the builder or answer 404."""
    builder = make_builder_admin_service().get_builder(builder_id)
    if builder is None:
        abort(404)
    return builder


def _builder_form_data(builder: Builder) -> dict:
    """Return the values that fill the form when an existing builder is opened."""
    values = {
        "key": builder.key,
        "preview_kind": builder.preview_kind.value,
        "sort_order": builder.sort_order,
        "is_visible": builder.is_visible,
    }
    for row in builder.translations:
        values[f"name_{row.language.code}"] = row.name
        values[f"hint_{row.language.code}"] = row.hint
    return values


def _render_builder_form(form: BuilderForm, builder: Builder | None) -> str:
    """Render the builder page: the form and, for an existing builder, its steps."""
    return render_template(
        "admin/builders/builder_form.html", form=form, builder=builder, text_of=text_of
    )


@admin_blueprint.get("/builders/new")
@permission_required(BUILDERS, EDIT)
def builder_new() -> str:
    """Show an empty builder form."""
    return _render_builder_form(BuilderForm(), None)


@admin_blueprint.get("/builders/<int:builder_id>")
@permission_required(BUILDERS)
def builder_edit(builder_id: int) -> str:
    """Show a builder and its steps (read-only for roles without edit access)."""
    builder = _load_builder(builder_id)
    return _render_builder_form(BuilderForm(data=_builder_form_data(builder)), builder)


def _save_builder(builder: Builder | None) -> Response | str:
    """Validate the builder form and save it."""
    service = make_builder_admin_service()
    form = BuilderForm()
    if form.validate_on_submit():
        try:
            saved = (
                service.update_builder(builder, form.to_input())
                if builder
                else service.create_builder(form.to_input())
            )
            db.session.commit()
        except BuilderAdminError as error:
            db.session.rollback()
            form.key.errors = [_key_error_message(error)]
        else:
            flash(get_translator()("admin.saved"), "success")
            return redirect(url_for("admin.builder_edit", builder_id=saved.id))
    flash(get_translator()("admin.form_error"), "error")
    return _render_builder_form(form, builder)


@admin_blueprint.post("/builders/new")
@permission_required(BUILDERS, EDIT)
def builder_create() -> Response | str:
    """Create a builder from the form."""
    return _save_builder(None)


@admin_blueprint.post("/builders/<int:builder_id>")
@permission_required(BUILDERS, EDIT)
def builder_update(builder_id: int) -> Response | str:
    """Save changes to a builder."""
    return _save_builder(_load_builder(builder_id))


@admin_blueprint.post("/builders/<int:builder_id>/delete")
@permission_required(BUILDERS, EDIT)
def builder_delete(builder_id: int) -> Response:
    """Delete a builder with its steps and options (past orders keep their own copy)."""
    paths = make_builder_admin_service().delete_builder(_load_builder(builder_id))
    db.session.commit()
    _delete_files(paths)
    flash(get_translator()("admin.deleted"), "success")
    return redirect(url_for("admin.builders"))


@admin_blueprint.post("/builders/<int:builder_id>/move")
@permission_required(BUILDERS, EDIT)
def builder_move(builder_id: int) -> Response:
    """Move a builder earlier or later in the list (direction=up|down)."""
    make_builder_admin_service().move_builder(_load_builder(builder_id), _direction())
    db.session.commit()
    return redirect(url_for("admin.builders"))


# --- steps -------------------------------------------------------------


def _load_step(step_id: int) -> BuilderStep:
    """Return the step or answer 404."""
    step = make_builder_admin_service().get_step(step_id)
    if step is None:
        abort(404)
    return step


def _role_choices(builder: Builder) -> list[tuple[str, str]]:
    """Return (value, label) pairs for the roles that fit this builder's picture."""
    translate = get_translator()
    return [
        (role.value, translate(f"admin.builders.role.{role.value or 'none'}"))
        for role in make_builder_admin_service().roles_for(builder.preview_kind)
    ]


def _step_form_data(step: BuilderStep) -> dict:
    """Return the values that fill the form when an existing step is opened."""
    values = {
        "key": step.key,
        "sort_order": step.sort_order,
        "is_multiple": step.is_multiple,
        "is_required": step.is_required,
        "is_base": step.is_base,
        "is_layered": step.is_layered,
        "preview_role": step.preview_role,
    }
    for row in step.translations:
        values[f"title_{row.language.code}"] = row.title
        values[f"hint_{row.language.code}"] = row.hint
    return values


def _render_step_form(form: StepForm, builder: Builder, step: BuilderStep | None) -> str:
    """Render the step page: the form and, for an existing step, its options."""
    return render_template(
        "admin/builders/step_form.html", form=form, builder=builder, step=step, text_of=text_of
    )


@admin_blueprint.get("/builders/<int:builder_id>/steps/new")
@permission_required(BUILDERS, EDIT)
def step_new(builder_id: int) -> str:
    """Show an empty step form for a builder."""
    builder = _load_builder(builder_id)
    form = StepForm()
    form.set_role_choices(_role_choices(builder))
    return _render_step_form(form, builder, None)


@admin_blueprint.get("/builders/steps/<int:step_id>")
@permission_required(BUILDERS)
def step_edit(step_id: int) -> str:
    """Show a step and its options (read-only for roles without edit access)."""
    step = _load_step(step_id)
    form = StepForm(data=_step_form_data(step))
    form.set_role_choices(_role_choices(step.builder))
    return _render_step_form(form, step.builder, step)


def _save_step(builder: Builder, step: BuilderStep | None) -> Response | str:
    """Validate the step form and save it."""
    service = make_builder_admin_service()
    form = StepForm()
    form.set_role_choices(_role_choices(builder))
    if form.validate_on_submit():
        try:
            saved = (
                service.update_step(step, form.to_input())
                if step
                else service.create_step(builder, form.to_input())
            )
            db.session.commit()
        except BuilderAdminError as error:
            db.session.rollback()
            form.key.errors = [_key_error_message(error)]
        else:
            flash(get_translator()("admin.saved"), "success")
            return redirect(url_for("admin.step_edit", step_id=saved.id))
    flash(get_translator()("admin.form_error"), "error")
    return _render_step_form(form, builder, step)


@admin_blueprint.post("/builders/<int:builder_id>/steps/new")
@permission_required(BUILDERS, EDIT)
def step_create(builder_id: int) -> Response | str:
    """Create a step from the form."""
    return _save_step(_load_builder(builder_id), None)


@admin_blueprint.post("/builders/steps/<int:step_id>")
@permission_required(BUILDERS, EDIT)
def step_update(step_id: int) -> Response | str:
    """Save changes to a step."""
    step = _load_step(step_id)
    return _save_step(step.builder, step)


@admin_blueprint.post("/builders/steps/<int:step_id>/delete")
@permission_required(BUILDERS, EDIT)
def step_delete(step_id: int) -> Response:
    """Delete a step with its options."""
    step = _load_step(step_id)
    builder_id = step.builder_id
    paths = make_builder_admin_service().delete_step(step)
    db.session.commit()
    _delete_files(paths)
    flash(get_translator()("admin.deleted"), "success")
    return redirect(url_for("admin.builder_edit", builder_id=builder_id))


@admin_blueprint.post("/builders/steps/<int:step_id>/move")
@permission_required(BUILDERS, EDIT)
def step_move(step_id: int) -> Response:
    """Move a step earlier or later inside its builder (direction=up|down)."""
    step = _load_step(step_id)
    make_builder_admin_service().move_step(step, _direction())
    db.session.commit()
    return redirect(url_for("admin.builder_edit", builder_id=step.builder_id))


# --- options -----------------------------------------------------------


def _load_option(option_id: int) -> BuilderOption:
    """Return the option or answer 404."""
    option = make_builder_admin_service().get_option(option_id)
    if option is None:
        abort(404)
    return option


def _option_form_data(option: BuilderOption) -> dict:
    """Return the values that fill the form when an existing option is opened."""
    values = {
        "key": option.key,
        "price": option.price,
        "sort_order": option.sort_order,
        "is_in_stock": option.is_in_stock,
        "is_visible": option.is_visible,
        "color": option.color,
        "shape": option.shape,
        "preview_amount": option.preview_amount,
    }
    for row in option.translations:
        values[f"name_{row.language.code}"] = row.name
    return values


def _render_option_form(form: OptionForm, step: BuilderStep, option: BuilderOption | None) -> str:
    """Render the option form page for a new or an existing option."""
    return render_template(
        "admin/builders/option_form.html",
        form=form,
        step=step,
        option=option,
        shapes=SHAPE_SUGGESTIONS,
        text_of=text_of,
    )


@admin_blueprint.get("/builders/steps/<int:step_id>/options/new")
@permission_required(BUILDERS, EDIT)
def option_new(step_id: int) -> str:
    """Show an empty option form for a step."""
    return _render_option_form(OptionForm(), _load_step(step_id), None)


@admin_blueprint.get("/builders/options/<int:option_id>")
@permission_required(BUILDERS)
def option_edit(option_id: int) -> str:
    """Show an option in the form (read-only for roles without edit access)."""
    option = _load_option(option_id)
    return _render_option_form(OptionForm(data=_option_form_data(option)), option.step, option)


def _save_option(step: BuilderStep, option: BuilderOption | None) -> Response | str:
    """Validate the option form, store the picture and the option, and answer the request."""
    service = make_builder_admin_service()
    storage = make_builder_image_storage()
    translate = get_translator()
    form = OptionForm()
    if not form.validate_on_submit():
        flash(translate("admin.form_error"), "error")
        return _render_option_form(form, step, option)

    upload = form.photo.data
    new_photo = None
    if upload is not None and getattr(upload, "filename", ""):
        try:
            new_photo = storage.save(upload.stream)
        except InvalidImageError as error:
            form.photo.errors = [translate(f"admin.menu.photo.error.{error.problem.value}")]
            flash(translate("admin.form_error"), "error")
            return _render_option_form(form, step, option)

    old_photo = None
    try:
        saved = (
            service.update_option(option, form.to_input())
            if option
            else service.create_option(step, form.to_input())
        )
        if new_photo:
            old_photo = service.set_option_image(saved, new_photo)
        elif form.remove_photo.data:
            old_photo = service.remove_option_image(saved)
        db.session.commit()
    except BuilderAdminError as error:
        db.session.rollback()
        storage.delete(new_photo)
        form.key.errors = [_key_error_message(error)]
        flash(translate("admin.form_error"), "error")
        return _render_option_form(form, step, option)
    storage.delete(old_photo)
    flash(translate("admin.saved"), "success")
    return redirect(url_for("admin.step_edit", step_id=saved.step_id))


@admin_blueprint.post("/builders/steps/<int:step_id>/options/new")
@permission_required(BUILDERS, EDIT)
def option_create(step_id: int) -> Response | str:
    """Create an option from the form."""
    return _save_option(_load_step(step_id), None)


@admin_blueprint.post("/builders/options/<int:option_id>")
@permission_required(BUILDERS, EDIT)
def option_update(option_id: int) -> Response | str:
    """Save changes to an option."""
    option = _load_option(option_id)
    return _save_option(option.step, option)


@admin_blueprint.post("/builders/options/<int:option_id>/delete")
@permission_required(BUILDERS, EDIT)
def option_delete(option_id: int) -> Response:
    """Delete an option and its picture (past orders keep their own copy of the name)."""
    option = _load_option(option_id)
    step_id = option.step_id
    path = make_builder_admin_service().delete_option(option)
    db.session.commit()
    _delete_files([path])
    flash(get_translator()("admin.deleted"), "success")
    return redirect(url_for("admin.step_edit", step_id=step_id))


@admin_blueprint.post("/builders/options/<int:option_id>/stock")
@permission_required(BUILDERS, EDIT)
def option_set_stock(option_id: int) -> Response:
    """Mark an option as available (value=1) or sold out (value=0)."""
    option = _load_option(option_id)
    make_builder_admin_service().set_option_in_stock(option, request.form.get("value") == "1")
    db.session.commit()
    return _back_to("admin.step_edit", step_id=option.step_id)


@admin_blueprint.post("/builders/options/<int:option_id>/visible")
@permission_required(BUILDERS, EDIT)
def option_set_visible(option_id: int) -> Response:
    """Show (value=1) or hide (value=0) an option on the public page."""
    option = _load_option(option_id)
    make_builder_admin_service().set_option_visible(option, request.form.get("value") == "1")
    db.session.commit()
    return _back_to("admin.step_edit", step_id=option.step_id)


@admin_blueprint.post("/builders/options/<int:option_id>/move")
@permission_required(BUILDERS, EDIT)
def option_move(option_id: int) -> Response:
    """Move an option earlier or later inside its step (direction=up|down)."""
    option = _load_option(option_id)
    make_builder_admin_service().move_option(option, _direction())
    db.session.commit()
    return redirect(url_for("admin.step_edit", step_id=option.step_id))
