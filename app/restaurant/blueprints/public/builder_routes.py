"""Builder pages: build a pizza, a sandwich or a drink and add it to the cart."""

from dataclasses import asdict

from flask import abort, flash, redirect, render_template, request, url_for
from werkzeug.wrappers import Response

from restaurant.blueprints.public import public_blueprint
from restaurant.constants import MAX_DISH_QUANTITY
from restaurant.language_context import get_active_language, get_translator
from restaurant.service_factory import make_builder_service, make_cart_service
from restaurant.services import CartError, CustomBuild, InvalidSelectionError


@public_blueprint.get("/build")
def builder() -> Response:
    """Open the first builder (the page has one address per kind of build)."""
    builders = make_builder_service().list_builders(get_active_language().code)
    if not builders:
        return redirect(url_for("public.menu"))
    return redirect(url_for("public.build", key=builders[0].key))


@public_blueprint.get("/build/<key>")
def build(key: str) -> str:
    """Show one builder: its steps, the picture and the live price."""
    service = make_builder_service()
    code = get_active_language().code
    current = service.get_builder(key, code)
    if current is None:
        abort(404)
    builder_data = asdict(current) | {"static_base": url_for("static", filename="")}
    return render_template(
        "build.html",
        builders=service.list_builders(code),
        current=current,
        builder_data=builder_data,
    )


@public_blueprint.post("/build/<key>")
def build_submit(key: str) -> Response:
    """Add a build to the cart without JavaScript (the page script uses the JSON API)."""
    translate = get_translator()
    quantity = request.form.get("quantity", 1, type=int)
    option_ids = [
        int(value)
        for field in request.form
        if field.startswith("step-")
        for value in request.form.getlist(field)
        if value.isdecimal()
    ]
    try:
        resolved = make_builder_service().resolve(key, option_ids, get_active_language().code)
        if resolved is None or not 1 <= quantity <= MAX_DISH_QUANTITY:
            abort(404 if resolved is None else 400)
        make_cart_service().add_custom(
            CustomBuild(resolved.builder_id, resolved.option_ids), quantity
        )
    except InvalidSelectionError as error:
        flash(translate(f"builder.error.{error.problem.value}"), "warning")
        return redirect(url_for("public.build", key=key))
    except CartError:
        flash(translate("cart.error"), "warning")
        return redirect(url_for("public.build", key=key))
    return redirect(url_for("public.cart"))
