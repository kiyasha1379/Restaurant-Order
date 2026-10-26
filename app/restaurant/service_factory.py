"""Factory functions that wire services to repositories and the database session.

Blueprints and commands call these instead of building the chain by hand,
so the wiring is written once (technical plan, section 9).
"""

from flask import current_app, url_for
from flask_login import current_user

from restaurant.cart_session import AccountCartStorage, SessionCartStorage
from restaurant.extensions import db
from restaurant.media import ImageStorage, VideoStorage
from restaurant.repositories import (
    AddressRepository,
    BackgroundRepository,
    BuilderRepository,
    CategoryRepository,
    ContactMessageRepository,
    DishRepository,
    LanguageRepository,
    OrderRepository,
    PaymentRepository,
    PermissionRepository,
    ReservationRepository,
    RoleRepository,
    ScheduleRepository,
    SettingRepository,
    SiteSectionRepository,
    TableRepository,
    UiStringRepository,
    UserRepository,
    VerificationCodeRepository,
)
from restaurant.seed.demo_customers import DemoCustomerSeeder
from restaurant.seed.demo_staff import DemoStaffSeeder
from restaurant.seed.seed_service import DemoSeedService
from restaurant.services import (
    AccessService,
    AuthService,
    BackgroundService,
    BookingService,
    BuilderAdminService,
    BuilderService,
    BuildResolver,
    CartService,
    CodeIssuer,
    ContactService,
    CustomerAdminService,
    CustomerAuthService,
    CustomerProfileService,
    DashboardService,
    FixedCodeIssuer,
    FixedDeliveryFee,
    LanguageAdminService,
    LanguageService,
    LoggedCodeIssuer,
    MenuAdminService,
    MenuService,
    OrderBoardService,
    OrderService,
    PaymentGateway,
    PaymentService,
    PricingService,
    ReorderService,
    ScheduleService,
    SettingsAdminService,
    SiteAppearanceService,
    SiteSettingsService,
    StaffService,
    TableAdminService,
    TranslationService,
    create_gateway,
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
        TableRepository(db.session),
        ScheduleRepository(db.session),
    )


def make_cart_service() -> CartService:
    """Build a CartService; a signed-in customer's cart is also saved with the account."""
    session_storage = SessionCartStorage()
    if current_user.is_authenticated:
        return CartService(
            AccountCartStorage(session_storage, current_user._get_current_object(), db.session)
        )
    return CartService(session_storage)


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


def make_payment_gateway() -> PaymentGateway:
    """Build the gateway named by the PAYMENT_GATEWAY setting."""

    def mock_page_url(authority: str, language_code: str) -> str:
        return url_for("public.mock_gateway_page", lang_code=language_code, authority=authority)

    return create_gateway(current_app.config["PAYMENT_GATEWAY"], mock_page_url)


def make_payment_service() -> PaymentService:
    """Build a PaymentService on the current session."""
    return PaymentService(
        db.session,
        PaymentRepository(db.session),
        make_order_service(),
        make_payment_gateway(),
    )


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


def make_schedule_service() -> ScheduleService:
    """Build a ScheduleService on the current session."""
    return ScheduleService(ScheduleRepository(db.session))


def make_booking_service() -> BookingService:
    """Build a BookingService on the current session."""
    return BookingService(
        db.session,
        TableRepository(db.session),
        ReservationRepository(db.session),
        make_schedule_service(),
        make_site_settings_service(),
    )


def make_table_admin_service() -> TableAdminService:
    """Build a TableAdminService on the current session."""
    return TableAdminService(TableRepository(db.session), ReservationRepository(db.session))


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


def make_settings_admin_service() -> SettingsAdminService:
    """Build a SettingsAdminService on the current session."""
    return SettingsAdminService(make_site_settings_service(), make_language_admin_service())


def make_code_issuer() -> CodeIssuer:
    """Pick where verification codes come from: a fixed code in demo mode, else a logged one."""
    if current_app.config["DEMO_MODE"] or current_app.config["TESTING"]:
        return FixedCodeIssuer(current_app.config["DEMO_VERIFICATION_CODE"])
    return LoggedCodeIssuer()


def make_customer_auth_service() -> CustomerAuthService:
    """Build a CustomerAuthService on the current session."""
    return CustomerAuthService(
        UserRepository(db.session),
        VerificationCodeRepository(db.session),
        OrderRepository(db.session),
        ReservationRepository(db.session),
        make_code_issuer(),
        current_app.config["SECRET_KEY"],
    )


def make_customer_profile_service() -> CustomerProfileService:
    """Build a CustomerProfileService on the current session."""
    return CustomerProfileService(UserRepository(db.session), AddressRepository(db.session))


def make_reorder_service() -> ReorderService:
    """Build a ReorderService on the current session."""
    return ReorderService(make_pricing_service())


def make_contact_service() -> ContactService:
    """Build a ContactService on the current session."""
    return ContactService(ContactMessageRepository(db.session))


def make_customer_admin_service() -> CustomerAdminService:
    """Build a CustomerAdminService on the current session."""
    return CustomerAdminService(
        UserRepository(db.session),
        OrderRepository(db.session),
        ReservationRepository(db.session),
        AddressRepository(db.session),
    )


def make_demo_customer_seeder() -> DemoCustomerSeeder:
    """Build a DemoCustomerSeeder on the current session."""
    return DemoCustomerSeeder(
        UserRepository(db.session),
        AddressRepository(db.session),
        ContactMessageRepository(db.session),
    )


def make_site_appearance_service() -> SiteAppearanceService:
    """Build a SiteAppearanceService on the current session."""
    return SiteAppearanceService(
        SiteSectionRepository(db.session),
        BackgroundRepository(db.session),
        make_language_admin_service(),
    )


def make_logo_storage() -> ImageStorage:
    """Build the photo storage for the logo (kept at a larger size than dish photos)."""
    return ImageStorage(current_app.config["UPLOAD_FOLDER"], folder="site", max_side=600)


def make_poster_storage() -> ImageStorage:
    """Build the photo storage for background posters (full-screen size)."""
    return ImageStorage(current_app.config["UPLOAD_FOLDER"], folder="backgrounds", max_side=1920)


def make_video_storage() -> VideoStorage:
    """Build the storage for background videos."""
    return VideoStorage(current_app.config["UPLOAD_FOLDER"])
