"""Menu management: dishes (with photo upload) and categories."""

from flask import abort, flash, redirect, render_template, request, url_for
from werkzeug.wrappers import Response

from restaurant.blueprints.admin import admin_blueprint
from restaurant.blueprints.admin.guards import is_safe_admin_path, permission_required
from restaurant.constants import LANGUAGE_CODE_ENGLISH as EN
from restaurant.constants import AccessLevel, PermissionKey
from restaurant.extensions import db
from restaurant.forms.admin_menu_forms import CategoryForm, DishForm
from restaurant.language_context import get_active_language, get_translator
from restaurant.media import InvalidImageError
from restaurant.models import Category, Dish
from restaurant.service_factory import make_image_storage, make_menu_admin_service
from restaurant.services import (
    CategoryNotEmptyError,
    DuplicateSlugError,
    InvalidSlugError,
    MenuAdminError,
)
from restaurant.services.localized import pick_translation

MENU = PermissionKey.MENU
EDIT = AccessLevel.EDIT
DIRECTIONS = {"up": -1, "down": 1}


def display_name(translations, language_code: str, fallback: str) -> str:  # noqa: ANN001
    """Return the name of a menu row in the panel language (Persian when missing)."""
    translation = pick_translation(translations, language_code)
    return translation.name if translation and translation.name else fallback


def _back_to(default_endpoint: str, **values) -> Response:  # noqa: ANN003 - url_for values
    """Redirect to `next` when it is a panel address, else to the default page."""
    target = request.form.get("next")
    return redirect(target if is_safe_admin_path(target) else url_for(default_endpoint, **values))


def _category_choices(service) -> list[tuple[int, str]]:  # noqa: ANN001 - MenuAdminService
    """Return (id, name) pairs for the category select, in menu order."""
    code = get_active_language().code
    return [
        (category.id, display_name(category.translations, code, category.slug))
        for category in service.list_categories()
    ]


# --- dish list ---------------------------------------------------------


@admin_blueprint.get("/menu")
@permission_required(MENU)
def menu() -> str:
    """Show every dish by category; `?category=<id>` narrows it, `?missing=en` lists gaps."""
    service = make_menu_admin_service()
    category_id = request.args.get("category", type=int)
    missing_english = request.args.get("missing") == EN
    categories = service.list_categories()
    dishes = service.list_dishes(category_id)
    if missing_english:
        dishes = [dish for dish in dishes if not _has_translation(dish, EN)]
    groups = [
        (category, [dish for dish in dishes if dish.category_id == category.id])
        for category in categories
    ]
    return render_template(
        "admin/menu/list.html",
        groups=[(category, items) for category, items in groups if items or not category_id],
        categories=categories,
        category_id=category_id,
        missing_english=missing_english,
        display_name=display_name,
        has_translation=_has_translation,
    )


def _has_translation(dish: Dish, language_code: str) -> bool:
    """Return True when the dish has a name in this language."""
    return any(row.language.code == language_code and row.name for row in dish.translations)


def _load_dish(dish_id: int) -> Dish:
    """Return the dish or answer 404."""
    dish = make_menu_admin_service().get_dish(dish_id)
    if dish is None:
        abort(404)
    return dish


@admin_blueprint.post("/menu/dishes/<int:dish_id>/stock")
@permission_required(MENU, EDIT)
def dish_set_stock(dish_id: int) -> Response:
    """Mark a dish as available (value=1) or sold out (value=0)."""
    make_menu_admin_service().set_in_stock(_load_dish(dish_id), request.form.get("value") == "1")
    db.session.commit()
    return _back_to("admin.menu")


@admin_blueprint.post("/menu/dishes/<int:dish_id>/visible")
@permission_required(MENU, EDIT)
def dish_set_visible(dish_id: int) -> Response:
    """Show (value=1) or hide (value=0) a dish on the public menu."""
    make_menu_admin_service().set_visible(_load_dish(dish_id), request.form.get("value") == "1")
    db.session.commit()
    return _back_to("admin.menu")


@admin_blueprint.post("/menu/dishes/<int:dish_id>/move")
@permission_required(MENU, EDIT)
def dish_move(dish_id: int) -> Response:
    """Move a dish up or down inside its category (direction=up|down)."""
    direction = DIRECTIONS.get(request.form.get("direction", ""))
    if direction is None:
        abort(400)
    make_menu_admin_service().move_dish(_load_dish(dish_id), direction)
    db.session.commit()
    return _back_to("admin.menu")


# --- dish form ---------------------------------------------------------


def _dish_form_data(dish: Dish) -> dict:
    """Return the values that fill the form when an existing dish is opened."""
    values = {
        "category_id": dish.category_id,
        "base_price": dish.base_price,
        "sort_order": dish.sort_order,
        "is_in_stock": dish.is_in_stock,
        "is_chefs_pick": dish.is_chefs_pick,
        "is_visible": dish.is_visible,
    }
    for row in dish.translations:
        code = row.language.code
        values[f"name_{code}"] = row.name
        values[f"description_{code}"] = row.description
        values[f"ingredients_{code}"] = row.ingredients
        values[f"serving_note_{code}"] = row.serving_note
    return values


def _render_dish_form(form: DishForm, dish: Dish | None) -> str:
    """Render the dish form page for a new or an existing dish."""
    return render_template("admin/menu/dish_form.html", form=form, dish=dish)


@admin_blueprint.get("/menu/dishes/new")
@permission_required(MENU, EDIT)
def dish_new() -> str:
    """Show an empty dish form."""
    service = make_menu_admin_service()
    form = DishForm()
    form.set_category_choices(_category_choices(service))
    first_category = request.args.get("category", type=int)
    if first_category in {value for value, _ in form.category_id.choices}:
        form.category_id.data = first_category
    return _render_dish_form(form, None)


@admin_blueprint.get("/menu/dishes/<int:dish_id>")
@permission_required(MENU)
def dish_edit(dish_id: int) -> str:
    """Show a dish in the form (read-only for roles without edit access)."""
    dish = _load_dish(dish_id)
    form = DishForm(data=_dish_form_data(dish))
    form.set_category_choices(_category_choices(make_menu_admin_service()))
    return _render_dish_form(form, dish)


def _save_dish(dish: Dish | None) -> Response | str:
    """Validate the dish form, store the photo and the dish, and answer the request."""
    service = make_menu_admin_service()
    storage = make_image_storage()
    translate = get_translator()
    form = DishForm()
    form.set_category_choices(_category_choices(service))
    if not form.validate_on_submit():
        flash(translate("admin.form_error"), "error")
        return _render_dish_form(form, dish)

    upload = form.photo.data
    new_photo = None
    if upload is not None and getattr(upload, "filename", ""):
        try:
            new_photo = storage.save(upload.stream)
        except InvalidImageError as error:
            form.photo.errors = [translate(f"admin.menu.photo.error.{error.problem.value}")]
            flash(translate("admin.form_error"), "error")
            return _render_dish_form(form, dish)

    old_photo = None
    try:
        saved = (
            service.update_dish(dish, form.to_input())
            if dish
            else service.create_dish(form.to_input())
        )
        if new_photo:
            old_photo = service.set_photo(saved, new_photo)
        elif form.remove_photo.data:
            old_photo = service.remove_photo(saved)
        db.session.commit()
    except MenuAdminError:
        db.session.rollback()
        storage.delete(new_photo)
        flash(translate("admin.form_error"), "error")
        return _render_dish_form(form, dish)
    storage.delete(old_photo)
    flash(translate("admin.saved"), "success")
    return redirect(url_for("admin.dish_edit", dish_id=saved.id))


@admin_blueprint.post("/menu/dishes/new")
@permission_required(MENU, EDIT)
def dish_create() -> Response | str:
    """Create a dish from the form."""
    return _save_dish(None)


@admin_blueprint.post("/menu/dishes/<int:dish_id>")
@permission_required(MENU, EDIT)
def dish_update(dish_id: int) -> Response | str:
    """Save changes to a dish."""
    return _save_dish(_load_dish(dish_id))


@admin_blueprint.post("/menu/dishes/<int:dish_id>/delete")
@permission_required(MENU, EDIT)
def dish_delete(dish_id: int) -> Response:
    """Delete a dish and its photo (past orders keep their own copy of the name and price)."""
    dish = _load_dish(dish_id)
    paths = make_menu_admin_service().delete_dish(dish)
    db.session.commit()
    storage = make_image_storage()
    for path in paths:
        storage.delete(path)
    flash(get_translator()("admin.deleted"), "success")
    return redirect(url_for("admin.menu"))


# --- categories --------------------------------------------------------


@admin_blueprint.get("/menu/categories")
@permission_required(MENU)
def categories() -> str:
    """List the categories with their order, visibility and dish counts."""
    return render_template(
        "admin/menu/categories.html",
        categories=make_menu_admin_service().list_categories(),
        display_name=display_name,
    )


def _load_category(category_id: int) -> Category:
    """Return the category or answer 404."""
    category = make_menu_admin_service().get_category(category_id)
    if category is None:
        abort(404)
    return category


def _category_form_data(category: Category) -> dict:
    """Return the values that fill the form when an existing category is opened."""
    values = {
        "slug": category.slug,
        "sort_order": category.sort_order,
        "is_visible": category.is_visible,
    }
    for row in category.translations:
        values[f"name_{row.language.code}"] = row.name
    return values


@admin_blueprint.get("/menu/categories/new")
@permission_required(MENU, EDIT)
def category_new() -> str:
    """Show an empty category form."""
    return render_template("admin/menu/category_form.html", form=CategoryForm(), category=None)


@admin_blueprint.get("/menu/categories/<int:category_id>")
@permission_required(MENU)
def category_edit(category_id: int) -> str:
    """Show a category in the form (read-only for roles without edit access)."""
    category = _load_category(category_id)
    return render_template(
        "admin/menu/category_form.html",
        form=CategoryForm(data=_category_form_data(category)),
        category=category,
    )


def _save_category(category: Category | None) -> Response | str:
    """Validate the category form and save it."""
    service = make_menu_admin_service()
    translate = get_translator()
    form = CategoryForm()
    if form.validate_on_submit():
        try:
            if category:
                service.update_category(category, form.to_input())
            else:
                service.create_category(form.to_input())
            db.session.commit()
        except (InvalidSlugError, DuplicateSlugError) as error:
            db.session.rollback()
            key = "duplicate" if isinstance(error, DuplicateSlugError) else "invalid"
            form.slug.errors = [translate(f"admin.menu.error.slug_{key}")]
        else:
            flash(translate("admin.saved"), "success")
            return redirect(url_for("admin.categories"))
    flash(translate("admin.form_error"), "error")
    return render_template("admin/menu/category_form.html", form=form, category=category)


@admin_blueprint.post("/menu/categories/new")
@permission_required(MENU, EDIT)
def category_create() -> Response | str:
    """Create a category from the form."""
    return _save_category(None)


@admin_blueprint.post("/menu/categories/<int:category_id>")
@permission_required(MENU, EDIT)
def category_update(category_id: int) -> Response | str:
    """Save changes to a category."""
    return _save_category(_load_category(category_id))


@admin_blueprint.post("/menu/categories/<int:category_id>/delete")
@permission_required(MENU, EDIT)
def category_delete(category_id: int) -> Response:
    """Delete an empty category."""
    try:
        make_menu_admin_service().delete_category(_load_category(category_id))
        db.session.commit()
    except CategoryNotEmptyError:
        db.session.rollback()
        flash(get_translator()("admin.menu.error.category_not_empty"), "error")
    else:
        flash(get_translator()("admin.deleted"), "success")
    return redirect(url_for("admin.categories"))


@admin_blueprint.post("/menu/categories/<int:category_id>/move")
@permission_required(MENU, EDIT)
def category_move(category_id: int) -> Response:
    """Move a category earlier or later in the menu (direction=up|down)."""
    direction = DIRECTIONS.get(request.form.get("direction", ""))
    if direction is None:
        abort(400)
    make_menu_admin_service().move_category(_load_category(category_id), direction)
    db.session.commit()
    return redirect(url_for("admin.categories"))
