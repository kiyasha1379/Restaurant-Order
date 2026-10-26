"""Orders: the live board, the history list, one order, status actions and the receipt."""

from flask import (
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    stream_with_context,
    url_for,
)
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from restaurant.blueprints.admin import admin_blueprint
from restaurant.blueprints.admin.guards import (
    current_profile,
    is_safe_admin_path,
    permission_required,
)
from restaurant.constants import AccessLevel, FulfillmentType, OrderStatus, PermissionKey
from restaurant.extensions import db
from restaurant.language_context import get_translator, reset_session_after_error
from restaurant.order_stream import ChangeStream
from restaurant.service_factory import make_order_board_service, make_order_service
from restaurant.services import InvalidTransitionError, OrderStatusMachine

ORDERS = PermissionKey.ORDERS
EDIT = AccessLevel.EDIT


def _next_status(order) -> OrderStatus | None:  # noqa: ANN001 - an Order row
    """Return the next normal status of the order, or None when it is finished."""
    return OrderStatusMachine.forward_step(order.status, order.fulfillment)


def _can_cancel(order) -> bool:  # noqa: ANN001 - an Order row
    """Return True while the order may still be cancelled."""
    return OrderStatusMachine.can_move(order.status, OrderStatus.CANCELLED, order.fulfillment)


def _order_template_values() -> dict:
    """Helpers every order template uses: the next step, cancel rule and money visibility."""
    return {
        "next_status": _next_status,
        "can_cancel": _can_cancel,
        "show_money": current_profile().can_see_money,
        "can_edit_orders": current_profile().can_edit(ORDERS),
    }


@admin_blueprint.get("/orders")
@permission_required(ORDERS)
def orders() -> str:
    """Show the live four-column board."""
    return render_template(
        "admin/orders/board.html",
        board=make_order_board_service().board(),
        **_order_template_values(),
    )


@admin_blueprint.get("/orders/board")
@permission_required(ORDERS)
def orders_board_fragment() -> str:
    """Return only the board columns (the page swaps them in when something changes)."""
    return render_template(
        "admin/orders/_board.html",
        board=make_order_board_service().board(),
        **_order_template_values(),
    )


@admin_blueprint.get("/orders/stream")
@permission_required(ORDERS)
def orders_stream() -> Response:
    """Stream "board" events whenever an order is placed or changes status."""
    service = make_order_board_service()

    def read_marker() -> str:
        # End the open read transaction first, or SQLite keeps showing the old snapshot.
        try:
            db.session.rollback()
            return service.change_marker()
        except SQLAlchemyError:
            current_app.logger.exception("Could not read the order marker")
            reset_session_after_error()
            raise

    stream = ChangeStream(
        read_marker,
        poll_seconds=current_app.config["ORDER_STREAM_POLL_SECONDS"],
        max_seconds=current_app.config["ORDER_STREAM_MAX_SECONDS"],
    )
    response = Response(stream_with_context(stream.events()), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


def _status_from_query(name: str) -> OrderStatus | None:
    """Read an order status from the query string; an unknown value means "any"."""
    try:
        return OrderStatus(request.args[name])
    except (KeyError, ValueError):
        return None


@admin_blueprint.get("/orders/history")
@permission_required(ORDERS)
def orders_history() -> str:
    """Show the order list with filters. Searching by name or phone needs the 'money' permission."""
    show_money = current_profile().can_see_money
    try:
        fulfillment = FulfillmentType(request.args["fulfillment"])
    except (KeyError, ValueError):
        fulfillment = None
    text = request.args.get("q", "").strip() if show_money else ""
    status = _status_from_query("status")
    page = request.args.get("page", 1, type=int)
    result = make_order_board_service().search(status, fulfillment, text, page)
    return render_template(
        "admin/orders/history.html",
        result=result,
        status=status,
        fulfillment=fulfillment,
        text=text,
        statuses=list(OrderStatus),
        **_order_template_values(),
    )


@admin_blueprint.get("/orders/<int:order_id>")
@permission_required(ORDERS)
def order_detail(order_id: int) -> str:
    """Show one order: lines, totals, customer, status history and the actions."""
    order = make_order_board_service().get(order_id)
    if order is None:
        abort(404)
    return render_template("admin/orders/detail.html", order=order, **_order_template_values())


@admin_blueprint.get("/orders/<int:order_id>/receipt")
@permission_required(ORDERS)
def order_receipt(order_id: int) -> str:
    """Show a print-friendly slip. Amounts and customer details follow the 'money' permission."""
    order = make_order_board_service().get(order_id)
    if order is None:
        abort(404)
    return render_template("admin/orders/receipt.html", order=order, **_order_template_values())


def _after_action(order_id: int) -> Response:
    """Go back to where the action came from (the board or the detail page)."""
    target = request.form.get("next")
    return redirect(
        target if is_safe_admin_path(target) else url_for("admin.order_detail", order_id=order_id)
    )


def _change_order(order_id: int, move) -> Response:  # noqa: ANN001 - a callable (service, order)
    """Load the order, apply `move`, save, and report a refused move."""
    service = make_order_service()
    order = service.get(order_id)
    if order is None:
        abort(404)
    try:
        move(service, order)
    except InvalidTransitionError:
        db.session.rollback()
        flash(get_translator()("admin.orders.error.transition"), "error")
    else:
        db.session.commit()
    return _after_action(order_id)


@admin_blueprint.post("/orders/<int:order_id>/advance")
@permission_required(ORDERS, EDIT)
def order_advance(order_id: int) -> Response:
    """Move the order one normal step forward."""
    return _change_order(order_id, lambda service, order: service.advance(order, current_user.id))


@admin_blueprint.post("/orders/<int:order_id>/cancel")
@permission_required(ORDERS, EDIT)
def order_cancel(order_id: int) -> Response:
    """Cancel the order (allowed until it is completed)."""
    return _change_order(
        order_id,
        lambda service, order: service.change_status(order, OrderStatus.CANCELLED, current_user.id),
    )
