"""The shopping cart: what a visitor has chosen so far, kept in a storage they own.

The cart never holds prices. It only remembers which dish and how many; the
server prices it every time (`PricingService`), so the browser cannot cheat.
"""

import hashlib
from dataclasses import dataclass
from typing import Protocol

from restaurant.constants import MAX_DISH_QUANTITY

# A cart lives in the session cookie (about 4 KB), so it holds a limited number of lines.
MAX_CART_LINES = 25


class CartError(ValueError):
    """The request cannot change the cart (unknown line, bad quantity...)."""


@dataclass(frozen=True)
class CustomBuild:
    """What a customer built: a builder and the chosen options in build order."""

    builder_id: int
    option_ids: tuple[int, ...]


@dataclass(frozen=True)
class CartLine:
    """One line of the cart. `line_id` is stable, so the browser can refer to it.

    A plain dish has a `dish_id`; a custom build has `custom` and no dish.
    """

    line_id: str
    dish_id: int | None
    quantity: int
    custom: CustomBuild | None = None


class CartStorage(Protocol):
    """Where the raw cart is kept. The web app uses the session; tests use a plain list."""

    def load(self) -> list[dict]:
        """Return the stored lines."""

    def save(self, raw_lines: list[dict]) -> None:
        """Replace the stored lines."""


class CartService:
    """Adds, changes and removes cart lines."""

    def __init__(self, storage: CartStorage) -> None:
        """Receive the storage instead of importing the session, so tests can swap it."""
        self._storage = storage

    def lines(self) -> list[CartLine]:
        """Return the cart lines. Damaged entries in the storage are ignored."""
        lines = []
        for raw in self._storage.load():
            line = self._parse(raw)
            if line is not None:
                lines.append(line)
        return lines

    def count(self) -> int:
        """Return the number of items (quantities added up), for the header badge."""
        return sum(line.quantity for line in self.lines())

    def add_dish(self, dish_id: int, quantity: int = 1) -> None:
        """Add a dish; adding it again raises the quantity of its line."""
        self._check_quantity(quantity, minimum=1)
        line_id = self.dish_line_id(dish_id)
        self._add_line(CartLine(line_id, dish_id, quantity))

    def add_custom(self, custom: CustomBuild, quantity: int = 1) -> None:
        """Add a custom build; building the same thing again raises the quantity of its line.

        The caller has already checked the build with the build resolver.
        """
        self._check_quantity(quantity, minimum=1)
        self._add_line(CartLine(self.custom_line_id(custom), None, quantity, custom))

    def _add_line(self, new_line: CartLine) -> None:
        """Insert a line, or add its quantity to the line that has the same id."""
        lines = {line.line_id: line for line in self.lines()}
        existing = lines.get(new_line.line_id)
        if existing is None and len(lines) >= MAX_CART_LINES:
            raise CartError("The cart has too many lines")
        total = (existing.quantity if existing else 0) + new_line.quantity
        lines[new_line.line_id] = CartLine(
            new_line.line_id, new_line.dish_id, min(total, MAX_DISH_QUANTITY), new_line.custom
        )
        self._store(list(lines.values()))

    def merge_saved(self, raw_lines: list[dict]) -> None:
        """Add the lines saved with an account to this cart (used when a customer signs in).

        The same line adds up (up to the quantity cap); lines beyond the cart limit are dropped.
        """
        lines = {line.line_id: line for line in self.lines()}
        for raw in raw_lines:
            saved = self._parse(raw)
            if saved is None:
                continue
            existing = lines.get(saved.line_id)
            if existing is None and len(lines) >= MAX_CART_LINES:
                continue
            total = (existing.quantity if existing else 0) + saved.quantity
            lines[saved.line_id] = CartLine(
                saved.line_id, saved.dish_id, min(total, MAX_DISH_QUANTITY), saved.custom
            )
        self._store(list(lines.values()))

    def set_quantity(self, line_id: str, quantity: int) -> None:
        """Set a line's quantity; zero removes the line."""
        self._check_quantity(quantity, minimum=0)
        lines = self.lines()
        if line_id not in {line.line_id for line in lines}:
            raise CartError("Unknown cart line")
        self._store(
            [
                (
                    CartLine(line.line_id, line.dish_id, quantity, line.custom)
                    if line.line_id == line_id
                    else line
                )
                for line in lines
                if quantity > 0 or line.line_id != line_id
            ]
        )

    def remove_lines(self, line_ids: set[str]) -> None:
        """Drop these lines (used when a dish is no longer available)."""
        self._store([line for line in self.lines() if line.line_id not in line_ids])

    def clear(self) -> None:
        """Empty the cart (after an order is placed)."""
        self._storage.save([])

    @staticmethod
    def dish_line_id(dish_id: int) -> str:
        """Return the line id used for a plain dish."""
        return f"dish-{dish_id}"

    @staticmethod
    def custom_line_id(custom: CustomBuild) -> str:
        """Return a line id that is the same for the same builder and the same options in order."""
        digest = hashlib.sha1(  # noqa: S324 - not security: only names a cart line
            f"{custom.builder_id}:{','.join(map(str, custom.option_ids))}".encode()
        ).hexdigest()
        return f"build-{digest[:12]}"

    @staticmethod
    def _check_quantity(quantity: int, minimum: int) -> None:
        """Reject quantities outside the allowed range."""
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise CartError("Quantity must be a whole number")
        if quantity < minimum or quantity > MAX_DISH_QUANTITY:
            raise CartError("Quantity is out of range")

    @staticmethod
    def _parse(raw: object) -> CartLine | None:
        """Turn a stored entry into a line, or None when it is damaged."""
        if not isinstance(raw, dict):
            return None
        try:
            quantity = int(raw["quantity"])
            if "builder_id" in raw:
                return CartService._parse_custom(raw, quantity)
            dish_id = int(raw["dish_id"])
        except (KeyError, TypeError, ValueError):
            return None
        if dish_id < 1 or not 0 < quantity <= MAX_DISH_QUANTITY:
            return None
        return CartLine(CartService.dish_line_id(dish_id), dish_id, quantity)

    @staticmethod
    def _parse_custom(raw: dict, quantity: int) -> CartLine | None:
        """Turn a stored custom build into a line, or None when it is damaged."""
        builder_id = int(raw["builder_id"])
        option_ids = tuple(int(option_id) for option_id in raw["option_ids"])
        if builder_id < 1 or not option_ids or min(option_ids) < 1:
            return None
        if not 0 < quantity <= MAX_DISH_QUANTITY:
            return None
        custom = CustomBuild(builder_id, option_ids)
        return CartLine(CartService.custom_line_id(custom), None, quantity, custom)

    def _store(self, lines: list[CartLine]) -> None:
        """Write the lines back to the storage."""
        self._storage.save([self._to_raw(line) for line in lines])

    @staticmethod
    def _to_raw(line: CartLine) -> dict:
        """Turn a line into the plain values kept in the storage."""
        if line.custom is not None:
            return {
                "builder_id": line.custom.builder_id,
                "option_ids": list(line.custom.option_ids),
                "quantity": line.quantity,
            }
        return {"dish_id": line.dish_id, "quantity": line.quantity}
