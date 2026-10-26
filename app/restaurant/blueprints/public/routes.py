"""Public routes. They only take the request and return a response."""

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.wrappers import Response

from restaurant.blueprints.public import public_blueprint
from restaurant.cart_web import load_priced_cart
from restaurant.constants import FulfillmentType
from restaurant.extensions import db
from restaurant.forms.checkout_form import CheckoutForm
from restaurant.language_context import (
    get_active_language,
    get_translator,
    reset_session_after_error,
)
from restaurant.service_factory import (
    make_cart_service,
    make_menu_service,
    make_order_service,
)
from restaurant.services import (
    EmptyCartError,
    InvalidTransitionError,
    OrderStatusMachine,
    PlaceOrderRequest,
    UnavailableDishError,
)

CHEFS_PICKS_ON_HOME = 4


@public_blueprint.get("/")
def home() -> str:
    """Show the home page: the full-screen sections, with the chef's picks."""
    language = get_active_language()
    try:
        dishes = make_menu_service().list_chefs_picks(language.code, CHEFS_PICKS_ON_HOME)
    except SQLAlchemyError:
        # The front door must open even when the database is not ready yet.
        current_app.logger.exception("Could not read the chef's picks")
        reset_session_after_error()
        dishes = []
    return render_template("home.html", dishes=dishes)


@public_blueprint.get("/menu")
def menu() -> str:
    """Show the menu. `?category=slug` opens it on one category (works without JavaScript).

    Every dish is on the page; the other categories are only hidden, so the chips
    can switch category instantly when JavaScript runs.
    """
    language = get_active_language()
    menu_service = make_menu_service()
    requested_slug = request.args.get("category", "")
    selected_slug = requested_slug if menu_service.has_category(requested_slug) else ""
    return render_template(
        "menu.html",
        categories=menu_service.list_categories(language.code),
        dishes=menu_service.list_dishes(language.code),
        selected_slug=selected_slug,
    )


@public_blueprint.get("/cart")
def cart() -> str:
    """Show the cart page (the lines are drawn by the page script from the cart API)."""
    return render_template("cart.html")


def _flash_unavailable_notice() -> None:
    """Tell the visitor that a dish left the cart because it can no longer be ordered."""
    flash(get_translator()("cart.removed_unavailable"), "warning")


@public_blueprint.route("/checkout", methods=["GET", "POST"])
def checkout() -> str | Response:
    """Show the checkout form and, when it is valid, place the order and go to its tracking page."""
    priced, removed = load_priced_cart()
    if removed:
        _flash_unavailable_notice()
    if not priced.lines:
        return redirect(url_for("public.cart"))
    if removed and request.method == "POST":
        # The cart changed under the customer: let them look at it again before ordering.
        return redirect(url_for("public.checkout"))

    form = CheckoutForm()
    if form.validate_on_submit():
        placed = _place_order(form)
        if placed is not None:
            return placed
        return redirect(url_for("public.checkout"))
    return render_template("checkout.html", form=form, priced=priced)


def _place_order(form: CheckoutForm) -> Response | None:
    """Place the order from the session cart. Returns the redirect, or None when it failed."""
    cart_service = make_cart_service()
    order_request = PlaceOrderRequest(
        customer_name=form.customer_name.data,
        customer_phone=form.customer_phone.data,
        fulfillment=form.fulfillment_type,
        delivery_address=form.delivery_address.data,
        note=form.note.data,
        payment_method=form.chosen_payment_method,
        language_code=get_active_language().code,
    )
    try:
        order = make_order_service().place_order(order_request, cart_service.lines())
        db.session.commit()
    except UnavailableDishError as error:
        db.session.rollback()
        cart_service.remove_lines(error.line_ids)
        _flash_unavailable_notice()
        return None
    except EmptyCartError:
        db.session.rollback()
        return redirect(url_for("public.cart"))
    cart_service.clear()
    return redirect(url_for("public.order_tracking", public_token=order.public_token))


@public_blueprint.get("/order/<public_token>")
def order_tracking(public_token: str) -> str:
    """Show an order with its live status. The unguessable token is the only key."""
    order = make_order_service().find_by_token(public_token)
    if order is None:
        abort(404)
    return render_template(
        "order.html",
        order=order,
        timeline=OrderStatusMachine.timeline(order.fulfillment),
        is_final=OrderStatusMachine.is_final(order.status),
        fulfillment_delivery=FulfillmentType.DELIVERY,
    )


@public_blueprint.post("/order/<public_token>/advance")
def demo_advance_order(public_token: str) -> Response:
    """Demo only: move an order one step forward, as the kitchen will do from the admin panel."""
    if not current_app.config["DEMO_MODE"]:
        abort(404)
    order_service = make_order_service()
    order = order_service.find_by_token(public_token)
    if order is None:
        abort(404)
    try:
        order_service.advance(order)
        db.session.commit()
    except InvalidTransitionError:
        db.session.rollback()
    return redirect(url_for("public.order_tracking", public_token=public_token))
