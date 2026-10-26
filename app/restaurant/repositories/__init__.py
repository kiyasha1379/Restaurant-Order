"""Repositories: the only code that writes database queries."""

from restaurant.repositories.access_repository import (
    PermissionRepository,
    RoleRepository,
    UserRepository,
)
from restaurant.repositories.background_repository import BackgroundRepository
from restaurant.repositories.base import BaseRepository
from restaurant.repositories.booking_repository import (
    ReservationRepository,
    ScheduleRepository,
    TableRepository,
)
from restaurant.repositories.builder_repository import BuilderRepository
from restaurant.repositories.customer_repository import (
    AddressRepository,
    ContactMessageRepository,
    VerificationCodeRepository,
)
from restaurant.repositories.language_repository import LanguageRepository
from restaurant.repositories.menu_repository import CategoryRepository, DishRepository
from restaurant.repositories.order_repository import CustomerOrderStats, OrderRepository
from restaurant.repositories.payment_repository import PaymentRepository
from restaurant.repositories.setting_repository import SettingRepository
from restaurant.repositories.site_section_repository import SiteSectionRepository
from restaurant.repositories.ui_string_repository import UiStringRepository

__all__ = [
    "AddressRepository",
    "ContactMessageRepository",
    "VerificationCodeRepository",
    "BackgroundRepository",
    "BaseRepository",
    "BuilderRepository",
    "CustomerOrderStats",
    "CategoryRepository",
    "DishRepository",
    "LanguageRepository",
    "OrderRepository",
    "PaymentRepository",
    "ReservationRepository",
    "ScheduleRepository",
    "TableRepository",
    "PermissionRepository",
    "RoleRepository",
    "SettingRepository",
    "SiteSectionRepository",
    "UiStringRepository",
    "UserRepository",
]
