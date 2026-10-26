"""The sections of the admin panel, in sidebar order.

Each section has one permission (technical plan, section 6). A section with
no page yet is simply not listed; later phases add their entries here.
"""

from dataclasses import dataclass

from restaurant.constants import PermissionKey


@dataclass(frozen=True)
class AdminSection:
    """One sidebar entry: its permission, its page and its label."""

    permission: PermissionKey
    endpoint: str
    icon: str
    label_key: str


ADMIN_SECTIONS: tuple[AdminSection, ...] = (
    AdminSection(PermissionKey.DASH, "admin.dashboard", "dash", "admin.nav.dash"),
    AdminSection(PermissionKey.ORDERS, "admin.orders", "orders", "admin.nav.orders"),
    AdminSection(PermissionKey.MENU, "admin.menu", "menu", "admin.nav.menu"),
    AdminSection(PermissionKey.LANGUAGES, "admin.languages", "languages", "admin.nav.languages"),
    AdminSection(PermissionKey.USERS, "admin.users", "users", "admin.nav.users"),
)
