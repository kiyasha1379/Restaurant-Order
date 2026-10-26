"""Online payment: start or retry a payment, the test gateway page and the callback."""

from flask import abort, flash, redirect, render_template, request, url_for
from werkzeug.wrappers import Response

from restaurant.blueprints.public import public_blueprint
from restaurant.constants import PaymentMethod, PaymentStatus
from restaurant.extensions import db
from restaurant.forms.checkout_form import available_payment_methods
from restaurant.language_context import get_translator
from restaurant.models.payment import MOCK_GATEWAY_NAME
from restaurant.payment_web import (
    flash_payment_problem,
    start_payment_response,
    tracking_redirect,
)
from restaurant.service_factory import make_order_service, make_payment_service
from restaurant.services import MockGateway, PaymentError, UnknownGatewayError
from restaurant.services.payment_service import PaymentProblem

RESULT_FLASH = {
    PaymentStatus.PAID: ("pay.flash.paid", "success"),
    PaymentStatus.FAILED: ("pay.flash.failed", "error"),
    PaymentStatus.CANCELLED: ("pay.flash.cancelled", "warning"),
}


def _find_order_or_404(public_token: str):  # noqa: ANN202 - an Order row
    """Return the order behind a tracking token or answer 404."""
    order = make_order_service().find_by_token(public_token)
    if order is None:
        abort(404)
    return order


def _payment_service_or_404():  # noqa: ANN202 - a PaymentService
    """Build the payment service; answer 404 when online payment is switched off."""
    try:
        return make_payment_service()
    except UnknownGatewayError:
        abort(404)


@public_blueprint.post("/pay/<public_token>/start")
def payment_start(public_token: str) -> Response:
    """Start (or retry) the online payment of an order that waits for it."""
    return start_payment_response(_find_order_or_404(public_token))


@public_blueprint.post("/pay/<public_token>/cash")
def payment_switch_to_cash(public_token: str) -> Response:
    """Let the customer pay on arrival after the online payment did not work out."""
    order = _find_order_or_404(public_token)
    try:
        if PaymentMethod.CASH_ON_SITE not in available_payment_methods():
            raise PaymentError(PaymentProblem.NOT_PAYABLE)
        _payment_service_or_404().switch_to_cash(order)
        db.session.commit()
    except PaymentError as error:
        db.session.rollback()
        flash_payment_problem(error.problem)
    else:
        flash(get_translator()("pay.flash.switched_to_cash"), "success")
    return tracking_redirect(order)


@public_blueprint.get("/pay/mock/<authority>")
def mock_gateway_page(authority: str) -> str | Response:
    """Show the test gateway: no card form, only the three outcomes a bank could report."""
    service = _payment_service_or_404()
    if service.gateway_name != MOCK_GATEWAY_NAME:
        abort(404)
    payment = service.find_open_payment(authority)
    if payment is None:
        abort(404)
    answers = {
        name: url_for(
            "public.payment_callback", gateway=MOCK_GATEWAY_NAME, authority=authority, status=value
        )
        for name, value in (
            ("success", MockGateway.STATUS_OK),
            ("failure", "failed"),
            ("cancel", MockGateway.STATUS_CANCEL),
        )
    }
    return render_template(
        "pay/mock_gateway.html", payment=payment, order=payment.order, answers=answers
    )


@public_blueprint.get("/pay/callback/<gateway>")
def payment_callback(gateway: str) -> Response:
    """Where the gateway sends the customer back; `verify()` decides if the order is paid."""
    service = _payment_service_or_404()
    if gateway != service.gateway_name:
        abort(404)
    try:
        result = service.complete(request.args)
        db.session.commit()
    except PaymentError as error:
        db.session.rollback()
        flash_payment_problem(error.problem)
        return redirect(url_for("public.menu"))
    message_key, category = RESULT_FLASH[result.payment.status]
    flash(get_translator()(message_key), category)
    return tracking_redirect(result.order)
