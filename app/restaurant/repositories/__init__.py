"""Repositories: the only code that writes database queries."""

from restaurant.repositories.access_repository import (
    PermissionRepository,
    RoleRepository,
    UserRepository,
)
from restaurant.repositories.background_repository import BackgroundRepository
from restaurant.repositories.base import BaseRepository
from restaurant.repositories.builder_repository import BuilderRepository
from restaurant.repositories.language_repository import LanguageRepository
from restaurant.repositories.menu_repository import CategoryRepository, DishRepository
from restaurant.repositories.order_repository import OrderRepository
from restaurant.repositories.setting_repository import SettingRepository
from restaurant.repositories.ui_string_repository import UiStringRepository

__all__ = [
    "BackgroundRepository",
    "BaseRepository",
    "BuilderRepository",
    "CategoryRepository",
    "DishRepository",
    "LanguageRepository",
    "OrderRepository",
    "PermissionRepository",
    "RoleRepository",
    "SettingRepository",
    "UiStringRepository",
    "UserRepository",
]
