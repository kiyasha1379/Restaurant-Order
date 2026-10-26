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
    """How the customer pays. Online payment arrives with the mock gateway (phase 9)."""

    CASH_ON_SITE = "cash_on_site"
    ONLINE = "online"


class OrderStatus(StrEnum):
    """Where an order is in its life. Allowed moves live in `order_status.py`."""

    PLACED = "placed"
    PREPARING = "preparing"
    READY = "ready"
    OUT_FOR_DELIVERY = "out_for_delivery"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SettingKey(StrEnum):
    """Keys of the `settings` table that the code reads."""

    BRAND_NAME = "brand_name"
    DELIVERY_FEE = "delivery_fee"
