"""The shopping cart: what a visitor has chosen so far, kept in a storage they own.

The cart never holds prices. It only remembers which dish and how many; the
server prices it every time (`PricingService`), so the browser cannot cheat.
"""

from dataclasses import dataclass
from typing import Protocol

from restaurant.constants import MAX_DISH_QUANTITY


class CartError(ValueError):
    """The request cannot change the cart (unknown line, bad quantity...)."""


@dataclass(frozen=True)
class CartLine:
    """One line of the cart. `line_id` is stable, so the browser can refer to it."""

    line_id: str
    dish_id: int
    quantity: int


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
        lines = {line.line_id: line for line in self.lines()}
        current = lines[line_id].quantity if line_id in lines else 0
        lines[line_id] = CartLine(line_id, dish_id, min(current + quantity, MAX_DISH_QUANTITY))
        self._store(list(lines.values()))

    def set_quantity(self, line_id: str, quantity: int) -> None:
        """Set a line's quantity; zero removes the line."""
        self._check_quantity(quantity, minimum=0)
        lines = self.lines()
        if line_id not in {line.line_id for line in lines}:
            raise CartError("Unknown cart line")
        self._store(
            [
                CartLine(line.line_id, line.dish_id, quantity) if line.line_id == line_id else line
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
            dish_id, quantity = int(raw["dish_id"]), int(raw["quantity"])
        except (KeyError, TypeError, ValueError):
            return None
        if dish_id < 1 or not 0 < quantity <= MAX_DISH_QUANTITY:
            return None
        return CartLine(CartService.dish_line_id(dish_id), dish_id, quantity)

    def _store(self, lines: list[CartLine]) -> None:
        """Write the lines back to the storage."""
        self._storage.save([{"dish_id": line.dish_id, "quantity": line.quantity} for line in lines])
