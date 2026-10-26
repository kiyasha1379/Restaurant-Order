"""Services: business rules, testable without the web server."""

from restaurant.services.access_service import NO_ACCESS, AccessProfile, AccessService
from restaurant.services.auth_service import (
    AuthService,
    LoginOutcome,
    LoginResult,
    WeakPasswordError,
)
from restaurant.services.background_service import BackgroundService, BackgroundView
from restaurant.services.cart_service import CartError, CartLine, CartService, CartStorage
from restaurant.services.dashboard_service import DashboardData, DashboardService
from restaurant.services.language_admin_service import (
    DefaultMustBeEnabledError,
    LanguageAdminError,
    LanguageAdminService,
    LanguageStatus,
    Progress,
    TextPage,
    TextRow,
)
from restaurant.services.language_service import FALLBACK_LANGUAGE, LanguageInfo, LanguageService
from restaurant.services.menu_admin_service import (
    CategoryInput,
    CategoryNotEmptyError,
    DishInput,
    DishTexts,
    DuplicateSlugError,
    InvalidSlugError,
    MenuAdminError,
    MenuAdminService,
    UnknownCategoryError,
)
from restaurant.services.menu_service import CategoryView, DishView, MenuService
from restaurant.services.order_board_service import (
    BOARD_COLUMNS,
    BoardColumn,
    BoardData,
    OrderBoardService,
    OrderPage,
)
from restaurant.services.order_service import (
    EmptyCartError,
    InvalidTransitionError,
    OrderError,
    OrderService,
    PlaceOrderRequest,
    UnavailableDishError,
)
from restaurant.services.order_status import OrderStatusMachine
from restaurant.services.pricing_service import (
    DeliveryFeeStrategy,
    FixedDeliveryFee,
    PricedCart,
    PricedLine,
    PricingService,
)
from restaurant.services.site_settings_service import SiteSettingsService
from restaurant.services.staff_service import (
    DuplicateEmailError,
    LockoutError,
    RoleInUseError,
    StaffError,
    StaffService,
    SystemRoleError,
    UnknownRoleError,
)
from restaurant.services.translation_service import SyncReport, TranslationService, Translator

__all__ = [
    "TextRow",
    "TextPage",
    "Progress",
    "LanguageStatus",
    "LanguageAdminService",
    "LanguageAdminError",
    "DefaultMustBeEnabledError",
    "UnknownCategoryError",
    "MenuAdminService",
    "MenuAdminError",
    "InvalidSlugError",
    "DuplicateSlugError",
    "DishTexts",
    "DishInput",
    "CategoryNotEmptyError",
    "CategoryInput",
    "OrderPage",
    "OrderBoardService",
    "BoardData",
    "BoardColumn",
    "BOARD_COLUMNS",
    "DashboardData",
    "DashboardService",
    "WeakPasswordError",
    "UnknownRoleError",
    "SystemRoleError",
    "StaffService",
    "StaffError",
    "RoleInUseError",
    "LoginResult",
    "LoginOutcome",
    "LockoutError",
    "DuplicateEmailError",
    "AuthService",
    "AccessProfile",
    "AccessService",
    "NO_ACCESS",
    "BackgroundService",
    "BackgroundView",
    "CartError",
    "CartLine",
    "CartService",
    "CartStorage",
    "CategoryView",
    "DeliveryFeeStrategy",
    "DishView",
    "EmptyCartError",
    "FALLBACK_LANGUAGE",
    "FixedDeliveryFee",
    "InvalidTransitionError",
    "LanguageInfo",
    "LanguageService",
    "MenuService",
    "OrderError",
    "OrderService",
    "OrderStatusMachine",
    "PlaceOrderRequest",
    "PricedCart",
    "PricedLine",
    "PricingService",
    "SiteSettingsService",
    "SyncReport",
    "TranslationService",
    "Translator",
    "UnavailableDishError",
]
