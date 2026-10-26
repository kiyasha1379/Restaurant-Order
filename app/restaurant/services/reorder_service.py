"""Ordering again: copies the lines of a past order into the cart if they can still be ordered."""

from dataclasses import dataclass

from restaurant.constants import MAX_DISH_QUANTITY
from restaurant.models import Order, OrderItem
from restaurant.services.cart_service import CartError, CartLine, CartService, CustomBuild
from restaurant.services.pricing_service import PricingService


@dataclass(frozen=True)
class ReorderResult:
    """How many lines went into the cart and how many could not be ordered again."""

    added: int
    skipped: int


class ReorderService:
    """Puts the lines of an old order back into a cart, using today's menu and prices."""

    def __init__(self, pricing_service: PricingService) -> None:
        """Receive the pricing service, which already knows what can be ordered now."""
        self._pricing_service = pricing_service

    def reorder(self, order: Order, cart: CartService, language_code: str) -> ReorderResult:
        """Add every orderable line of `order` to `cart`; the rest are counted as skipped."""
        wanted = [self._to_cart_line(item) for item in order.items]
        known = [line for line in wanted if line is not None]
        priced = self._pricing_service.price(known, order.fulfillment, language_code)
        added = 0
        for line in known:
            if line.line_id in priced.unavailable_line_ids:
                continue
            try:
                if line.custom is not None:
                    cart.add_custom(line.custom, line.quantity)
                else:
                    cart.add_dish(line.dish_id, line.quantity)
            except CartError:
                break
            added += 1
        return ReorderResult(added=added, skipped=len(wanted) - added)

    @staticmethod
    def _to_cart_line(item: OrderItem) -> CartLine | None:
        """Turn an order line into a cart line, or None when its links to the menu are gone."""
        quantity = min(item.quantity, MAX_DISH_QUANTITY)
        if item.builder_id is not None:
            option_ids = tuple(option.option_id for option in item.options)
            if not option_ids or None in option_ids:
                return None
            custom = CustomBuild(item.builder_id, option_ids)
            return CartLine(CartService.custom_line_id(custom), None, quantity, custom)
        if item.dish_id is None:
            return None
        return CartLine(CartService.dish_line_id(item.dish_id), item.dish_id, quantity)
