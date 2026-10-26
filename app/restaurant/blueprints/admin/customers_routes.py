"""Customers and messages: who signed up, what they ordered, and the contact-form inbox."""

from math import ceil

from flask import abort, flash, redirect, render_template, request, url_for
from werkzeug.wrappers import Response

from restaurant.blueprints.admin import admin_blueprint
from restaurant.blueprints.admin.guards import current_profile, permission_required
from restaurant.constants import AccessLevel, PermissionKey
from restaurant.extensions import db
from restaurant.language_context import get_translator
from restaurant.service_factory import make_contact_service, make_customer_admin_service

CUSTOMERS = PermissionKey.CUSTOMERS
EDIT = AccessLevel.EDIT
PAGE_SIZE = 20


def _page_number() -> int:
    """Read the page number from the address (1 when it is missing or wrong)."""
    return max(request.args.get("page", 1, type=int), 1)


@admin_blueprint.get("/customers")
@permission_required(CUSTOMERS)
def customers() -> str:
    """List customers, newest first, with a search box."""
    text = request.args.get("q", "").strip()
    page = _page_number()
    rows, total = make_customer_admin_service().list_customers(
        text, (page - 1) * PAGE_SIZE, PAGE_SIZE
    )
    return render_template(
        "admin/customers/list.html",
        rows=rows,
        total=total,
        text=text,
        page=page,
        pages=max(ceil(total / PAGE_SIZE), 1),
        show_money=current_profile().can_see_money,
        unread=make_contact_service().count_unread(),
    )


@admin_blueprint.get("/customers/<int:user_id>")
@permission_required(CUSTOMERS)
def customer_detail(user_id: int) -> str:
    """Show one customer with their orders, bookings and addresses."""
    detail = make_customer_admin_service().get_detail(user_id)
    if detail is None:
        abort(404)
    return render_template(
        "admin/customers/detail.html",
        detail=detail,
        show_money=current_profile().can_see_money,
    )


@admin_blueprint.post("/customers/<int:user_id>/active")
@permission_required(CUSTOMERS, EDIT)
def customer_active(user_id: int) -> Response:
    """Block or unblock a customer account."""
    make_active = request.form.get("active") == "1"
    if not make_customer_admin_service().set_active(user_id, make_active):
        abort(404)
    db.session.commit()
    key = "admin.customers.unblocked_done" if make_active else "admin.customers.blocked_done"
    flash(get_translator()(key), "success")
    return redirect(url_for("admin.customer_detail", user_id=user_id))


@admin_blueprint.get("/messages")
@permission_required(CUSTOMERS)
def messages() -> str:
    """Show the contact-form messages, newest first."""
    page = _page_number()
    service = make_contact_service()
    items, total = service.list_messages((page - 1) * PAGE_SIZE, PAGE_SIZE)
    return render_template(
        "admin/customers/messages.html",
        items=items,
        page=page,
        pages=max(ceil(total / PAGE_SIZE), 1),
        unread=service.count_unread(),
    )


@admin_blueprint.post("/messages/<int:message_id>/read")
@permission_required(CUSTOMERS, EDIT)
def message_read(message_id: int) -> Response:
    """Mark a message as read (or unread with `read=0`)."""
    if not make_contact_service().set_read(message_id, request.form.get("read") != "0"):
        abort(404)
    db.session.commit()
    return redirect(url_for("admin.messages", page=request.form.get("page", 1, type=int)))


@admin_blueprint.post("/messages/<int:message_id>/delete")
@permission_required(CUSTOMERS, EDIT)
def message_delete(message_id: int) -> Response:
    """Remove a message."""
    if not make_contact_service().delete(message_id):
        abort(404)
    db.session.commit()
    flash(get_translator()("admin.messages.deleted"), "success")
    return redirect(url_for("admin.messages"))
