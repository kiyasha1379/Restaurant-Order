"""Data models. Importing this package registers every table on `db.metadata`."""

from restaurant.models.access import Permission, Role, RolePermission, User, user_roles
from restaurant.models.background import Background
from restaurant.models.language import Language
from restaurant.models.menu import (
    Category,
    CategoryTranslation,
    Dish,
    DishImage,
    DishTranslation,
)
from restaurant.models.order import Order, OrderItem, OrderItemOption, OrderStatusLog
from restaurant.models.setting import Setting
from restaurant.models.ui_string import UiString, UiStringTranslation

__all__ = [
    "Background",
    "Category",
    "CategoryTranslation",
    "Dish",
    "DishImage",
    "DishTranslation",
    "Language",
    "Order",
    "OrderItem",
    "OrderItemOption",
    "OrderStatusLog",
    "Permission",
    "Role",
    "RolePermission",
    "Setting",
    "UiString",
    "UiStringTranslation",
    "User",
    "user_roles",
]
