"""Factory functions that wire services to repositories and the database session.

Blueprints and commands call these instead of building the chain by hand,
so the wiring is written once (technical plan, section 9).
"""

from flask import current_app

from restaurant.cart_session import SessionCartStorage
from restaurant.extensions import db
from restaurant.media import ImageStorage
from restaurant.repositories import (
    BackgroundRepository,
    BuilderRepository,
    CategoryRepository,
    DishRepository,
    LanguageRepository,
    OrderRepository,
    PermissionRepository,
    RoleRepository,
    SettingRepository,
    UiStringRepository,
    UserRepository,
)
from restaurant.seed.demo_staff import DemoStaffSeeder
from restaurant.seed.seed_service import DemoSeedService
from restaurant.services import (
    AccessService,
    AuthService,
    BackgroundService,
    BuilderAdminService,
    BuilderService,
    BuildResolver,
    CartService,
    DashboardService,
    FixedDeliveryFee,
    LanguageAdminService,
    LanguageService,
    MenuAdminService,
    MenuService,
    OrderBoardService,
    OrderService,
    PricingService,
    SiteSettingsService,
    StaffService,
    TranslationService,
)


def make_language_service() -> LanguageService:
    """Build a LanguageService on the current session."""
    return LanguageService(LanguageRepository(db.session))


def make_site_settings_service() -> SiteSettingsService:
    """Build a SiteSettingsService on the current session."""
    return SiteSettingsService(SettingRepository(db.session))


def make_translation_service() -> TranslationService:
    """Build a TranslationService on the current session."""
    return TranslationService(UiStringRepository(db.session), LanguageRepository(db.session))


def make_menu_service() -> MenuService:
    """Build a MenuService on the current session."""
    return MenuService(CategoryRepository(db.session), DishRepository(db.session))


def make_background_service() -> BackgroundService:
    """Build a BackgroundService on the current session."""
    return BackgroundService(BackgroundRepository(db.session))


def make_demo_seed_service() -> DemoSeedService:
    """Build a DemoSeedService on the current session."""
    return DemoSeedService(
        LanguageRepository(db.session),
        BackgroundRepository(db.session),
        CategoryRepository(db.session),
        DishRepository(db.session),
        BuilderRepository(db.session),
    )


def make_cart_service() -> CartService:
    """Build a CartService that keeps the cart in the visitor's session."""
    return CartService(SessionCartStorage())


def make_pricing_service() -> PricingService:
    """Build a PricingService with the delivery fee from the settings."""
    fee = make_site_settings_service().get_delivery_fee()
    return PricingService(DishRepository(db.session), FixedDeliveryFee(fee), make_build_resolver())


def make_build_resolver() -> BuildResolver:
    """Build a BuildResolver on the current session."""
    return BuildResolver(BuilderRepository(db.session))


def make_builder_service() -> BuilderService:
    """Build a BuilderService on the current session."""
    return BuilderService(BuilderRepository(db.session), make_build_resolver())


def make_order_service() -> OrderService:
    """Build an OrderService on the current session."""
    return OrderService(OrderRepository(db.session), make_pricing_service())


def make_access_service() -> AccessService:
    """Build an AccessService on the current session."""
    return AccessService(RoleRepository(db.session), PermissionRepository(db.session))


def make_auth_service() -> AuthService:
    """Build an AuthService on the current session."""
    return AuthService(UserRepository(db.session), make_access_service())


def make_staff_service() -> StaffService:
    """Build a StaffService on the current session."""
    return StaffService(
        UserRepository(db.session),
        RoleRepository(db.session),
        PermissionRepository(db.session),
        make_access_service(),
    )


def make_dashboard_service() -> DashboardService:
    """Build a DashboardService on the current session."""
    return DashboardService(
        OrderRepository(db.session), DishRepository(db.session), make_translation_service()
    )


def make_demo_staff_seeder() -> DemoStaffSeeder:
    """Build a DemoStaffSeeder on the current session."""
    return DemoStaffSeeder(
        make_access_service(),
        make_staff_service(),
        UserRepository(db.session),
        RoleRepository(db.session),
    )


def make_order_board_service() -> OrderBoardService:
    """Build an OrderBoardService on the current session."""
    return OrderBoardService(OrderRepository(db.session))


def make_menu_admin_service() -> MenuAdminService:
    """Build a MenuAdminService on the current session."""
    return MenuAdminService(
        CategoryRepository(db.session),
        DishRepository(db.session),
        LanguageRepository(db.session),
    )


def make_builder_admin_service() -> BuilderAdminService:
    """Build a BuilderAdminService on the current session."""
    return BuilderAdminService(BuilderRepository(db.session), LanguageRepository(db.session))


def make_image_storage() -> ImageStorage:
    """Build the photo storage that keeps files in the configured upload folder."""
    return ImageStorage(current_app.config["UPLOAD_FOLDER"])


def make_builder_image_storage() -> ImageStorage:
    """Build the photo storage for builder option pictures (their own upload folder)."""
    return ImageStorage(current_app.config["UPLOAD_FOLDER"], folder="builders")


def make_language_admin_service() -> LanguageAdminService:
    """Build a LanguageAdminService on the current session."""
    return LanguageAdminService(
        LanguageRepository(db.session),
        UiStringRepository(db.session),
        DishRepository(db.session),
        CategoryRepository(db.session),
    )
