"""The roles every installation starts with and what each may do.

`flask create-admin` and `flask seed-demo` create them if they are missing.
Existing roles are never changed, so edits made in the admin panel survive.
"""

from dataclasses import dataclass, field

from restaurant.constants import AccessLevel, PermissionKey

EDIT = AccessLevel.EDIT
VIEW = AccessLevel.VIEW

ADMIN_ROLE_KEY = "admin"


@dataclass(frozen=True)
class DefaultRole:
    """A starting role: its names and the level it has on some permissions (others are 'none')."""

    key: str
    name_fa: str
    name_en: str
    grants: dict[PermissionKey, AccessLevel] = field(default_factory=dict)
    is_system: bool = False


DEFAULT_ROLES: tuple[DefaultRole, ...] = (
    # The administrator always has full access; see AccessService.build_profile.
    DefaultRole(
        key=ADMIN_ROLE_KEY,
        name_fa="مدیر کل",
        name_en="Administrator",
        grants={key: EDIT for key in PermissionKey if key is not PermissionKey.MONEY}
        | {PermissionKey.MONEY: VIEW},
        is_system=True,
    ),
    DefaultRole(
        key="manager",
        name_fa="مدیر",
        name_en="Manager",
        grants={
            PermissionKey.DASH: VIEW,
            PermissionKey.ORDERS: EDIT,
            PermissionKey.MENU: EDIT,
            PermissionKey.BUILDERS: EDIT,
            PermissionKey.TABLES: EDIT,
            PermissionKey.CUSTOMERS: EDIT,
            PermissionKey.LANGUAGES: EDIT,
            PermissionKey.SITE: EDIT,
            PermissionKey.SETTINGS: EDIT,
            PermissionKey.MONEY: VIEW,
        },
    ),
    DefaultRole(
        key="cashier",
        name_fa="صندوقدار",
        name_en="Cashier",
        grants={
            PermissionKey.DASH: VIEW,
            PermissionKey.ORDERS: EDIT,
            PermissionKey.TABLES: EDIT,
            PermissionKey.CUSTOMERS: VIEW,
            PermissionKey.MONEY: VIEW,
        },
    ),
    # The kitchen sees the items of each order, never amounts or customer details.
    DefaultRole(
        key="kitchen",
        name_fa="آشپزخانه",
        name_en="Kitchen",
        grants={PermissionKey.ORDERS: EDIT},
    ),
    DefaultRole(
        key="viewer",
        name_fa="ناظر (فقط مشاهده)",
        name_en="Viewer (read only)",
        grants={key: VIEW for key in PermissionKey},
    ),
)
