"""Prices: the only place that works out what a cart costs.

The browser may show a preview, but the stored order always uses this
service's numbers (technical plan, section 7).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from restaurant.constants import FulfillmentType
from restaurant.repositories import DishRepository
from restaurant.services.build_resolver import (
    BuildResolver,
    InvalidSelectionError,
    PricedOption,
    ResolvedBuild,
)
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
    dish_id: int | None
    name: str
    name_fa: str
    name_en: str
    unit_price: int
    quantity: int
    line_total: int
    image_path: str | None
    # The chosen options of a custom build, in build order (empty for a plain dish).
    options: tuple[PricedOption, ...] = ()
    builder_id: int | None = None

    @property
    def summary(self) -> str:
        """Return the chosen option names in one line, for the cart and the receipt."""
        return "، ".join(option.name for option in self.options)


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
        self,
        dish_repository: DishRepository,
        delivery_fee_strategy: DeliveryFeeStrategy,
        build_resolver: BuildResolver,
    ) -> None:
        """Receive the repository, the fee rule and the build checker instead of importing them."""
        self._dish_repository = dish_repository
        self._delivery_fee_strategy = delivery_fee_strategy
        self._build_resolver = build_resolver

    def price(
        self, cart_lines: list[CartLine], fulfillment: FulfillmentType, language_code: str
    ) -> PricedCart:
        """Price the lines. Dishes that are hidden, sold out or gone are reported, not charged."""
        dish_ids = [line.dish_id for line in cart_lines if line.dish_id is not None]
        dishes = self._dish_repository.get_many(dish_ids)
        priced_lines: list[PricedLine] = []
        unavailable: set[str] = set()
        for cart_line in cart_lines:
            priced = (
                self._price_custom_line(cart_line, language_code)
                if cart_line.custom is not None
                else self._price_dish_line(cart_line, dishes.get(cart_line.dish_id), language_code)
            )
            if priced is None:
                unavailable.add(cart_line.line_id)
            else:
                priced_lines.append(priced)
        subtotal = sum(line.line_total for line in priced_lines)
        delivery_fee = self._delivery_fee_strategy.fee_for(fulfillment) if priced_lines else 0
        return PricedCart(
            lines=priced_lines,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=subtotal + delivery_fee,
            unavailable_line_ids=unavailable,
        )

    def _price_custom_line(self, cart_line: CartLine, language_code: str) -> PricedLine | None:
        """Price a custom build from the current options, or None when it is not valid now."""
        custom = cart_line.custom
        try:
            build = self._build_resolver.resolve(
                custom.builder_id, custom.option_ids, language_code
            )
        except InvalidSelectionError:
            return None
        return self._build_line(cart_line, build)

    @staticmethod
    def _build_line(cart_line: CartLine, build: ResolvedBuild) -> PricedLine:
        """Turn a resolved build into a priced line."""
        return PricedLine(
            line_id=cart_line.line_id,
            dish_id=None,
            name=build.name,
            name_fa=build.name_fa,
            name_en=build.name_en,
            unit_price=build.unit_price,
            quantity=cart_line.quantity,
            line_total=build.unit_price * cart_line.quantity,
            image_path=None,
            options=build.options,
            builder_id=build.builder_id,
        )

    def _price_dish_line(
        self, cart_line: CartLine, dish, language_code: str  # noqa: ANN001
    ) -> PricedLine | None:
        """Price a plain dish line, or None when the dish is hidden, sold out or gone."""
        if dish is None or not dish.is_visible or not dish.is_in_stock:
            return None
        return self._price_line(cart_line, dish, language_code)

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
