"""Web helpers for online payment: sending the customer to the gateway and reporting back."""

from flask import flash, redirect, url_for
from werkzeug.wrappers import Response

from restaurant.extensions import db
from restaurant.language_context import get_active_language, get_translator
from restaurant.models import Order
from restaurant.service_factory import make_payment_service
from restaurant.services import PaymentError, PaymentProblem, UnknownGatewayError

PROBLEM_MESSAGES = {
    PaymentProblem.NOT_PAYABLE: "pay.flash.not_payable",
    PaymentProblem.UNKNOWN_PAYMENT: "pay.flash.unknown",
    PaymentProblem.WRONG_GATEWAY: "pay.flash.unknown",
    PaymentProblem.GATEWAY_UNAVAILABLE: "pay.flash.unavailable",
    PaymentProblem.NOT_CASH: "pay.flash.not_payable",
}


def flash_payment_problem(problem: PaymentProblem) -> None:
    """Tell the customer why the payment step was refused."""
    flash(get_translator()(PROBLEM_MESSAGES[problem]), "error")


def tracking_redirect(order: Order) -> Response:
    """Go to the order's tracking page."""
    return redirect(url_for("public.order_tracking", public_token=order.public_token))


def start_payment_response(order: Order) -> Response:
    """Register an online attempt and send the customer to the gateway.

    When the gateway cannot be reached the order stays waiting for payment and the
    customer lands on its tracking page with a message and the retry button.
    """
    language_code = get_active_language().code
    try:
        service = make_payment_service()
        callback_url = url_for(
            "public.payment_callback", gateway=service.gateway_name, _external=True
        )
        started = service.start_online(order, callback_url, language_code)
        db.session.commit()
    except PaymentError as error:
        db.session.rollback()
        flash_payment_problem(error.problem)
        return tracking_redirect(order)
    except UnknownGatewayError:
        db.session.rollback()
        flash_payment_problem(PaymentProblem.GATEWAY_UNAVAILABLE)
        return tracking_redirect(order)
    return redirect(started.redirect_url)
