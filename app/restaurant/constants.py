"""Named constants and enums shared by several layers.

Keeping them in one module means a rule such as "the site has exactly two
languages" is written once and imported everywhere (no magic strings).
"""

from enum import StrEnum

TIMEZONE_NAME = "Asia/Tehran"

# The site is fixed to two languages (technical plan, section 7).
LANGUAGE_CODE_PERSIAN = "fa"
LANGUAGE_CODE_ENGLISH = "en"
SUPPORTED_LANGUAGE_CODES = (LANGUAGE_CODE_PERSIAN, LANGUAGE_CODE_ENGLISH)
DEFAULT_LANGUAGE_CODE = LANGUAGE_CODE_PERSIAN

DEFAULT_BRAND_NAME = "Restaurant"
# Fixed delivery fee in tomans until delivery zones arrive (phase 10).
DEFAULT_DELIVERY_FEE = 30_000
MAX_DISH_QUANTITY = 20
# Reservation rules start from these values; the admin panel changes them (settings table).
DEFAULT_RESERVATION_MAX_ADVANCE_DAYS = 30
DEFAULT_RESERVATION_DURATION_MINUTES = 90
DEFAULT_RESERVATION_SLOT_MINUTES = 30
DEFAULT_RESERVATION_MIN_NOTICE_MINUTES = 30
DEFAULT_OPENING_TIME = "12:00"
DEFAULT_CLOSING_TIME = "23:00"
MIN_PASSWORD_LENGTH = 8


class TextDirection(StrEnum):
    """Writing direction of a language; becomes the `dir` attribute of <html>."""

    RTL = "rtl"
    LTR = "ltr"


class MobileBackgroundMode(StrEnum):
    """What a background shows on phones and slow connections."""

    POSTER_ONLY = "poster_only"
    VIDEO = "video"


class AccessLevel(StrEnum):
    """How much of an admin section a role may use (technical plan, section 6)."""

    NONE = "none"
    VIEW = "view"
    EDIT = "edit"

    @property
    def rank(self) -> int:
        """Order of the levels: none < view < edit."""
        return _ACCESS_RANK[self]

    def allows(self, required: "AccessLevel") -> bool:
        """Return True when this level is at least as high as `required`."""
        return self.rank >= required.rank


_ACCESS_RANK = {AccessLevel.NONE: 0, AccessLevel.VIEW: 1, AccessLevel.EDIT: 2}


class PermissionKey(StrEnum):
    """One admin section, or the separate 'money' permission (technical plan, section 6)."""

    DASH = "dash"
    ORDERS = "orders"
    MENU = "menu"
    BUILDERS = "builders"
    TABLES = "tables"
    CUSTOMERS = "customers"
    LANGUAGES = "languages"
    USERS = "users"
    SITE = "site"
    SETTINGS = "settings"
    MONEY = "money"


class FulfillmentType(StrEnum):
    """How the customer gets the order."""

    TAKEAWAY = "takeaway"
    DELIVERY = "delivery"


class PaymentMethod(StrEnum):
    """How the customer pays: on arrival, or online through the configured gateway."""

    CASH_ON_SITE = "cash_on_site"
    ONLINE = "online"


class PaymentStatus(StrEnum):
    """Where one payment is. Only a verified payment is `paid`."""

    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OrderStatus(StrEnum):
    """Where an order is in its life. Allowed moves live in `order_status.py`."""

    AWAITING_PAYMENT = "awaiting_payment"
    PLACED = "placed"
    PREPARING = "preparing"
    READY = "ready"
    OUT_FOR_DELIVERY = "out_for_delivery"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReservationStatus(StrEnum):
    """Where a table reservation is. Only confirmed reservations hold a table."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


# Python's `date.weekday()` numbers Monday 0 ... Sunday 6. The Persian week starts on Saturday.
WEEKDAYS_SATURDAY_FIRST = (5, 6, 0, 1, 2, 3, 4)


class SettingKey(StrEnum):
    """Keys of the `settings` table that the code reads."""

    BRAND_NAME = "brand_name"
    DELIVERY_FEE = "delivery_fee"
    RESERVATION_MAX_ADVANCE_DAYS = "reservation_max_advance_days"
    RESERVATION_DURATION_MINUTES = "reservation_duration_minutes"
    RESERVATION_SLOT_MINUTES = "reservation_slot_minutes"
    RESERVATION_MIN_NOTICE_MINUTES = "reservation_min_notice_minutes"
    RESERVATION_AUTO_CONFIRM = "reservation_auto_confirm"
    ONLINE_PAYMENT_ENABLED = "online_payment_enabled"
    CASH_PAYMENT_ENABLED = "cash_payment_enabled"
    ORDERING_PAUSED = "ordering_paused"
    LOGO_PATH = "logo_path"
    ACCENT_COLOR = "accent_color"


DEFAULT_ACCENT_COLOR = "#e3a64b"  # the --color-accent token in tokens.css


class HomeSectionKey(StrEnum):
    """The home page sections the owner can reorder or hide (the hero and the footer are fixed)."""

    MODES = "modes"
    DISHES = "dishes"
    HOW = "how"
    RESERVE = "reserve"


# The order of the movable home sections before the owner changes anything.
DEFAULT_HOME_SECTION_ORDER = tuple(HomeSectionKey)

# Every background the site draws, in the order the admin lists them.
BACKGROUND_KEYS = (
    "home-hero",
    "home-showcase",
    "home-modes",
    "home-dishes",
    "home-how",
    "home-reserve",
    "home-footer",
    "menu-page",
    "builder-page",
    "reserve-page",
)


class PreviewKind(StrEnum):
    """Which picture a builder draws next to its steps. `plain` draws none."""

    PIZZA = "pizza"
    SANDWICH = "sandwich"
    DRINK = "drink"
    PLAIN = "plain"


class PreviewRole(StrEnum):
    """What a step does in the picture; each builder kind understands some of these."""

    NONE = ""
    CRUST = "crust"
    SAUCE = "sauce"
    CHEESE = "cheese"
    TOPPING = "topping"
    BREAD = "bread"
    LAYER = "layer"
    BASE = "base"
    SIZE = "size"
    FLAVOR = "flavor"
    EXTRA = "extra"


# The roles a step may have in each kind of picture (the admin form offers only these).
PREVIEW_ROLES_BY_KIND: dict[PreviewKind, tuple[PreviewRole, ...]] = {
    PreviewKind.PIZZA: (
        PreviewRole.NONE,
        PreviewRole.CRUST,
        PreviewRole.SAUCE,
        PreviewRole.CHEESE,
        PreviewRole.TOPPING,
    ),
    PreviewKind.SANDWICH: (PreviewRole.NONE, PreviewRole.BREAD, PreviewRole.LAYER),
    PreviewKind.DRINK: (
        PreviewRole.NONE,
        PreviewRole.BASE,
        PreviewRole.SIZE,
        PreviewRole.FLAVOR,
        PreviewRole.EXTRA,
    ),
    PreviewKind.PLAIN: (PreviewRole.NONE,),
}
