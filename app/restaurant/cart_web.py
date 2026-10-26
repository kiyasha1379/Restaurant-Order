"""Glue between the cart service, pricing and the web layer (pages and JSON API)."""

from restaurant.constants import FulfillmentType
from restaurant.language_context import get_active_language
from restaurant.service_factory import (
    make_cart_service,
    make_pricing_service,
    make_site_settings_service,
)
from restaurant.services import PricedCart, PricedLine


def load_priced_cart(
    fulfillment: FulfillmentType = FulfillmentType.TAKEAWAY,
) -> tuple[PricedCart, bool]:
    """Price the visitor's cart in the page language.

    Dishes that are no longer orderable are dropped from the cart. The second
    value tells the caller that this happened, so it can say so.
    """
    cart_service = make_cart_service()
    priced = make_pricing_service().price(
        cart_service.lines(), fulfillment, get_active_language().code
    )
    if priced.unavailable_line_ids:
        cart_service.remove_lines(priced.unavailable_line_ids)
    return priced, bool(priced.unavailable_line_ids)


def count_cart_items() -> int:
    """Return the number of items in the cart, for the header badge."""
    return make_cart_service().count()


def line_to_dict(line: PricedLine) -> dict:
    """Describe a priced line for JSON."""
    return {
        "line_id": line.line_id,
        "dish_id": line.dish_id,
        "name": line.name,
        "summary": line.summary,
        "unit_price": line.unit_price,
        "quantity": line.quantity,
        "line_total": line.line_total,
        "image_path": line.image_path,
    }


def cart_to_dict(priced: PricedCart, removed_unavailable: bool = False) -> dict:
    """Describe a priced cart for JSON (the browser formats the numbers itself)."""
    return {
        "count": priced.item_count,
        "lines": [line_to_dict(line) for line in priced.lines],
        "subtotal": priced.subtotal,
        "delivery_fee": priced.delivery_fee,
        "total": priced.total,
        "removed_unavailable": removed_unavailable,
    }


def is_ordering_paused() -> bool:
    """Return True while the restaurant has paused online ordering (a setting in the panel)."""
    return make_site_settings_service().is_ordering_paused()
