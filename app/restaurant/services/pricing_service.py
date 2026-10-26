"""Prices: the only place that works out what a cart costs.

The browser may show a preview, but the stored order always uses this
service's numbers (technical plan, section 7).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from restaurant.constants import FulfillmentType
from restaurant.repositories import DishRepository
from restaurant.services.cart_service import CartLine
from restaurant.services.localized import exact_translation, pick_translation


class DeliveryFeeStrategy(ABC):
    """A rule for the delivery fee. Delivery zones add another rule in phase 10."""

    @abstractmethod
    def fee_for(self, fulfillment: FulfillmentType) -> int:
        """Return the fee in tomans for this way of receiving the order."""


class FixedDeliveryFee(DeliveryFeeStrategy):
    """One fixed fee for every delivery; takeaway is free."""

    def __init__(self, amount: int) -> None:
        """Remember the fee in tomans."""
        self._amount = amount

    def fee_for(self, fulfillment: FulfillmentType) -> int:
        """Charge the fixed fee for delivery only."""
        return self._amount if fulfillment is FulfillmentType.DELIVERY else 0


@dataclass(frozen=True)
class PricedLine:
    """A cart line with the names and prices the server worked out."""

    line_id: str
    dish_id: int
    name: str
    name_fa: str
    name_en: str
    unit_price: int
    quantity: int
    line_total: int
    image_path: str | None


@dataclass(frozen=True)
class PricedCart:
    """A whole priced cart. `unavailable_line_ids` lists lines that could not be priced."""

    lines: list[PricedLine]
    subtotal: int
    delivery_fee: int
    total: int
    unavailable_line_ids: set[str] = field(default_factory=set)

    @property
    def item_count(self) -> int:
        """Return the quantities added up."""
        return sum(line.quantity for line in self.lines)


class PricingService:
    """Prices cart lines from the current menu."""

    def __init__(
        self, dish_repository: DishRepository, delivery_fee_strategy: DeliveryFeeStrategy
    ) -> None:
        """Receive the repository and the fee rule instead of importing them."""
        self._dish_repository = dish_repository
        self._delivery_fee_strategy = delivery_fee_strategy

    def price(
        self, cart_lines: list[CartLine], fulfillment: FulfillmentType, language_code: str
    ) -> PricedCart:
        """Price the lines. Dishes that are hidden, sold out or gone are reported, not charged."""
        dishes = self._dish_repository.get_many([line.dish_id for line in cart_lines])
        priced_lines: list[PricedLine] = []
        unavailable: set[str] = set()
        for cart_line in cart_lines:
            dish = dishes.get(cart_line.dish_id)
            if dish is None or not dish.is_visible or not dish.is_in_stock:
                unavailable.add(cart_line.line_id)
                continue
            priced_lines.append(self._price_line(cart_line, dish, language_code))
        subtotal = sum(line.line_total for line in priced_lines)
        delivery_fee = self._delivery_fee_strategy.fee_for(fulfillment) if priced_lines else 0
        return PricedCart(
            lines=priced_lines,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=subtotal + delivery_fee,
            unavailable_line_ids=unavailable,
        )

    @staticmethod
    def _price_line(cart_line: CartLine, dish, language_code: str) -> PricedLine:  # noqa: ANN001
        """Price one line and copy the names of the dish in both languages."""
        display = pick_translation(dish.translations, language_code)
        persian = exact_translation(dish.translations, "fa") or display
        english = exact_translation(dish.translations, "en")
        name_fa = persian.name if persian else f"#{dish.id}"
        image = dish.images[0] if dish.images else None
        return PricedLine(
            line_id=cart_line.line_id,
            dish_id=dish.id,
            name=display.name if display else name_fa,
            name_fa=name_fa,
            name_en=english.name if english else "",
            unit_price=dish.base_price,
            quantity=cart_line.quantity,
            line_total=dish.base_price * cart_line.quantity,
            image_path=image.path if image else None,
        )
