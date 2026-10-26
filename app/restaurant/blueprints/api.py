"""JSON and streaming endpoints used by the page scripts. No language prefix (plan, section 5)."""

from flask import Blueprint, Response, abort, current_app, jsonify, request, stream_with_context
from sqlalchemy.exc import SQLAlchemyError

from restaurant.cart_web import cart_to_dict, load_priced_cart
from restaurant.constants import MAX_DISH_QUANTITY, FulfillmentType, OrderStatus
from restaurant.extensions import db
from restaurant.language_context import (
    find_available_language,
    get_active_language,
    get_translator,
    reset_session_after_error,
    set_active_language,
)
from restaurant.order_stream import OrderStatusStream
from restaurant.service_factory import (
    make_builder_service,
    make_cart_service,
    make_menu_service,
    make_order_service,
)
from restaurant.services import (
    CartError,
    CustomBuild,
    InvalidSelectionError,
    OrderStatusMachine,
    SelectionProblem,
)

api_blueprint = Blueprint("api", __name__, url_prefix="/api")

LANGUAGE_PARAMETER = "lang"
STATUS_STREAM_POLL_SECONDS_KEY = "ORDER_STREAM_POLL_SECONDS"
STATUS_STREAM_MAX_SECONDS_KEY = "ORDER_STREAM_MAX_SECONDS"


@api_blueprint.before_request
def choose_language() -> None:
    """Answer in the language the page asks for (`?lang=fa`), else the default."""
    code = request.args.get(LANGUAGE_PARAMETER, "")
    language = find_available_language(code) if code else None
    if language is not None:
        set_active_language(language)


def json_error(translation_key: str, status_code: int) -> tuple[Response, int]:
    """Return a JSON error with a message in the page language."""
    return jsonify(error=get_translator()(translation_key)), status_code


def cart_response(removed_unavailable: bool = False) -> Response:
    """Return the current priced cart as JSON."""
    priced, removed = load_priced_cart()
    return jsonify(cart_to_dict(priced, removed or removed_unavailable))


@api_blueprint.get("/cart")
def get_cart() -> Response:
    """Return the cart."""
    return cart_response()


@api_blueprint.post("/cart/add")
def add_to_cart() -> Response | tuple[Response, int]:
    """Add a dish to the cart: {"dish_id": 3, "quantity": 1}."""
    body = request.get_json(silent=True) or {}
    dish_id, quantity = body.get("dish_id"), body.get("quantity", 1)
    if not isinstance(dish_id, int) or isinstance(dish_id, bool) or dish_id < 1:
        return json_error("cart.error", 400)
    if not make_menu_service().is_orderable(dish_id):
        return json_error("cart.removed_unavailable", 409)
    try:
        make_cart_service().add_dish(dish_id, quantity)
    except CartError:
        return json_error("cart.error", 400)
    return cart_response()


@api_blueprint.post("/cart/update")
def update_cart() -> Response | tuple[Response, int]:
    """Change a line's quantity (0 removes it): {"line_id": "dish-3", "quantity": 2}."""
    body = request.get_json(silent=True) or {}
    line_id, quantity = body.get("line_id"), body.get("quantity")
    if not isinstance(line_id, str):
        return json_error("cart.error", 400)
    try:
        make_cart_service().set_quantity(line_id, quantity)
    except CartError:
        return json_error("cart.error", 400)
    return cart_response()


def read_build_body() -> tuple[list[int], int] | None:
    """Read {"option_ids": [..], "quantity": n} from the request; None when it is malformed."""
    body = request.get_json(silent=True) or {}
    option_ids, quantity = body.get("option_ids"), body.get("quantity", 1)
    valid_ids = isinstance(option_ids, list) and all(
        isinstance(value, int) and not isinstance(value, bool) for value in option_ids
    )
    valid_quantity = (
        isinstance(quantity, int)
        and not isinstance(quantity, bool)
        and 1 <= quantity <= MAX_DISH_QUANTITY
    )
    if not valid_ids or not valid_quantity:
        return None
    return option_ids, quantity


def build_error(problem: SelectionProblem) -> tuple[Response, int]:
    """Answer a refused build in the page language."""
    status_code = 409 if problem is SelectionProblem.UNAVAILABLE else 400
    return json_error(f"builder.error.{problem.value}", status_code)


@api_blueprint.post("/builders/<key>/quote")
def build_quote(key: str) -> Response | tuple[Response, int]:
    """Price a build: {"option_ids": [3, 7], "quantity": 2}. The server's price is final."""
    parsed = read_build_body()
    if parsed is None:
        return json_error("cart.error", 400)
    option_ids, quantity = parsed
    try:
        quote = make_builder_service().quote(key, option_ids, quantity, get_active_language().code)
    except InvalidSelectionError as error:
        return build_error(error.problem)
    if quote is None:
        abort(404)
    return jsonify(unit_price=quote.unit_price, quantity=quote.quantity, total=quote.total)


@api_blueprint.post("/cart/add-custom")
def add_custom_to_cart() -> Response | tuple[Response, int]:
    """Add a build: {"builder": "pizza", "option_ids": [3, 7], "quantity": 1}."""
    parsed = read_build_body()
    builder_key = (request.get_json(silent=True) or {}).get("builder")
    if parsed is None or not isinstance(builder_key, str):
        return json_error("cart.error", 400)
    option_ids, quantity = parsed
    try:
        build = make_builder_service().resolve(builder_key, option_ids, get_active_language().code)
    except InvalidSelectionError as error:
        return build_error(error.problem)
    if build is None:
        abort(404)
    try:
        make_cart_service().add_custom(CustomBuild(build.builder_id, build.option_ids), quantity)
    except CartError:
        return json_error("cart.error", 400)
    return cart_response()


@api_blueprint.get("/quote")
def quote() -> Response | tuple[Response, int]:
    """Price the session cart for a way of receiving it: ?fulfillment=delivery."""
    try:
        fulfillment = FulfillmentType(request.args.get("fulfillment", FulfillmentType.TAKEAWAY))
    except ValueError:
        return json_error("cart.error", 400)
    priced, removed = load_priced_cart(fulfillment)
    return jsonify(cart_to_dict(priced, removed))


def describe_status(status: OrderStatus) -> dict:
    """Describe a status for the tracking page: its name, its label and whether it is final."""
    translate = get_translator()
    return {
        "status": status.value,
        "label": translate(f"order.status.{status.value}"),
        "final": OrderStatusMachine.is_final(status),
    }


def find_order_or_404(public_token: str):  # noqa: ANN201
    """Return the order for a tracking token or answer 404."""
    order = make_order_service().find_by_token(public_token)
    if order is None:
        abort(404)
    return order


@api_blueprint.get("/orders/<public_token>/status")
def order_status(public_token: str) -> Response:
    """Return the current status (the polling fallback of the stream)."""
    return jsonify(describe_status(find_order_or_404(public_token).status))


@api_blueprint.get("/orders/<public_token>/stream")
def order_stream(public_token: str) -> Response:
    """Stream status changes as server-sent events."""
    order_id = find_order_or_404(public_token).id
    order_service = make_order_service()

    def read_status() -> OrderStatus:
        # End the open read transaction first: SQLite would otherwise keep showing
        # the snapshot from the start of the stream.
        try:
            db.session.rollback()
            return order_service.read_status(order_id)
        except SQLAlchemyError:
            current_app.logger.exception("Could not read the order status")
            reset_session_after_error()
            raise

    stream = OrderStatusStream(
        read_status=read_status,
        describe=describe_status,
        is_final=OrderStatusMachine.is_final,
        poll_seconds=current_app.config[STATUS_STREAM_POLL_SECONDS_KEY],
        max_seconds=current_app.config[STATUS_STREAM_MAX_SECONDS_KEY],
    )
    response = Response(stream_with_context(stream.events()), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"  # tell nginx not to hold the stream back
    return response
