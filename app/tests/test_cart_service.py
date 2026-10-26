"""CartService rules, tested with a plain-list storage (constructor injection)."""

import pytest

from restaurant.constants import MAX_DISH_QUANTITY
from restaurant.services import CartError, CartLine, CartService


class FakeStorage:
    def __init__(self, raw=None):
        self.raw = raw if raw is not None else []

    def load(self):
        return self.raw

    def save(self, raw_lines):
        self.raw = raw_lines


@pytest.fixture
def cart():
    return CartService(FakeStorage())


def test_new_cart_is_empty(cart):
    assert cart.lines() == [] and cart.count() == 0


def test_adding_a_dish_creates_a_line(cart):
    cart.add_dish(3)
    assert cart.lines() == [CartLine("dish-3", 3, 1)]


def test_adding_the_same_dish_again_raises_its_quantity(cart):
    cart.add_dish(3)
    cart.add_dish(3, 2)
    assert cart.lines() == [CartLine("dish-3", 3, 3)]
    assert cart.count() == 3


def test_quantity_is_capped(cart):
    cart.add_dish(3, MAX_DISH_QUANTITY)
    cart.add_dish(3, 5)
    assert cart.lines()[0].quantity == MAX_DISH_QUANTITY


def test_set_quantity_changes_one_line_only(cart):
    cart.add_dish(1)
    cart.add_dish(2)
    cart.set_quantity("dish-2", 4)
    assert {line.line_id: line.quantity for line in cart.lines()} == {"dish-1": 1, "dish-2": 4}


def test_zero_quantity_removes_the_line(cart):
    cart.add_dish(1)
    cart.add_dish(2)
    cart.set_quantity("dish-1", 0)
    assert [line.line_id for line in cart.lines()] == ["dish-2"]


def test_unknown_line_is_rejected(cart):
    with pytest.raises(CartError):
        cart.set_quantity("dish-9", 1)


@pytest.mark.parametrize("quantity", [0, -1, MAX_DISH_QUANTITY + 1, "2", 1.5, True, None])
def test_bad_quantity_is_rejected_when_adding(cart, quantity):
    with pytest.raises(CartError):
        cart.add_dish(1, quantity)


@pytest.mark.parametrize("quantity", [-1, MAX_DISH_QUANTITY + 1, "2", None])
def test_bad_quantity_is_rejected_when_updating(cart, quantity):
    cart.add_dish(1)
    with pytest.raises(CartError):
        cart.set_quantity("dish-1", quantity)


def test_remove_lines_and_clear(cart):
    for dish_id in (1, 2, 3):
        cart.add_dish(dish_id)
    cart.remove_lines({"dish-1", "dish-3"})
    assert [line.dish_id for line in cart.lines()] == [2]
    cart.clear()
    assert cart.lines() == []


def test_damaged_storage_entries_are_ignored():
    storage = FakeStorage(
        [
            {"dish_id": 1, "quantity": 2},
            "junk",
            {"dish_id": "x", "quantity": 1},
            {"dish_id": 2},
            {"dish_id": 3, "quantity": 0},
            {"dish_id": 4, "quantity": 999},
            {"dish_id": -1, "quantity": 1},
        ]
    )
    assert CartService(storage).lines() == [CartLine("dish-1", 1, 2)]


def test_the_cart_stores_no_prices(cart):
    cart.add_dish(1)
    assert set(cart._storage.raw[0]) == {"dish_id", "quantity"}
