"""Data models. Importing this package registers every table on `db.metadata`."""

from restaurant.models.access import Permission, Role, RolePermission, User, user_roles
from restaurant.models.background import Background
from restaurant.models.booking import DiningTable, OpeningHour, Reservation, SpecialClosure
from restaurant.models.builder import (
    Builder,
    BuilderOption,
    BuilderOptionTranslation,
    BuilderStep,
    BuilderStepTranslation,
    BuilderTranslation,
)
from restaurant.models.customer import Address, ContactMessage, VerificationCode
from restaurant.models.language import Language
from restaurant.models.menu import (
    Category,
    CategoryTranslation,
    Dish,
    DishImage,
    DishTranslation,
)
from restaurant.models.order import Order, OrderItem, OrderItemOption, OrderStatusLog
from restaurant.models.payment import Payment
from restaurant.models.setting import Setting
from restaurant.models.site_section import SiteSection
from restaurant.models.ui_string import UiString, UiStringTranslation

__all__ = [
    "Address",
    "Background",
    "Builder",
    "BuilderOption",
    "BuilderOptionTranslation",
    "BuilderStep",
    "BuilderStepTranslation",
    "BuilderTranslation",
    "Category",
    "CategoryTranslation",
    "ContactMessage",
    "Dish",
    "DishImage",
    "DishTranslation",
    "DiningTable",
    "Language",
    "OpeningHour",
    "Order",
    "OrderItem",
    "OrderItemOption",
    "OrderStatusLog",
    "Payment",
    "Permission",
    "Reservation",
    "Role",
    "RolePermission",
    "Setting",
    "SiteSection",
    "SpecialClosure",
    "UiString",
    "UiStringTranslation",
    "User",
    "VerificationCode",
    "user_roles",
]
