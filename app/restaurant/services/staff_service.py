"""Managing staff accounts and roles from the admin panel."""

import re
import secrets
from collections.abc import Collection, Mapping

from restaurant.constants import AccessLevel, PermissionKey
from restaurant.models import Role, RolePermission, User
from restaurant.repositories import PermissionRepository, RoleRepository, UserRepository
from restaurant.services.access_service import AccessService
from restaurant.services.auth_service import hash_password

KEY_SUFFIX_BYTES = 3
MAX_KEY_LENGTH = 30


class StaffError(ValueError):
    """A staff or role change was refused."""


class DuplicateEmailError(StaffError):
    """Another account already uses this e-mail address."""


class UnknownRoleError(StaffError):
    """A role id does not exist."""


class LockoutError(StaffError):
    """The change would leave nobody able to manage users and roles."""


class SystemRoleError(StaffError):
    """The administrator role cannot be changed or deleted."""


class RoleInUseError(StaffError):
    """The role still has users."""


class StaffService:
    """Creates and changes staff accounts, roles and the permission matrix."""

    def __init__(
        self,
        user_repository: UserRepository,
        role_repository: RoleRepository,
        permission_repository: PermissionRepository,
        access_service: AccessService,
    ) -> None:
        """Receive the collaborators instead of importing them, so tests can swap them."""
        self._users = user_repository
        self._roles = role_repository
        self._permissions = permission_repository
        self._access = access_service

    # --- staff accounts -------------------------------------------------

    def list_staff(self) -> list[User]:
        """Return everyone who holds a role."""
        return self._users.list_staff()

    def get_user(self, user_id: int) -> User | None:
        """Return the user with this id, or None."""
        return self._users.get(user_id)

    def create_staff(
        self, email: str, display_name: str, password: str, role_ids: Collection[int]
    ) -> User:
        """Add a staff account. Raises DuplicateEmailError, WeakPasswordError, UnknownRoleError."""
        email = email.strip().lower()
        if self._users.get_by_email(email) is not None:
            raise DuplicateEmailError(email)
        user = User(
            email=email,
            display_name=display_name.strip(),
            password_hash=hash_password(password),
            is_active=True,
            roles=self._load_roles(role_ids),
        )
        return self._users.add(user)

    def update_staff(
        self,
        user: User,
        display_name: str,
        role_ids: Collection[int],
        is_active: bool,
        new_password: str = "",
    ) -> User:
        """Change a staff account; a blank `new_password` keeps the old one.

        Raises LockoutError when nobody would be left to manage users.
        """
        user.display_name = display_name.strip()
        user.roles = self._load_roles(role_ids)
        user.is_active = is_active
        if new_password:
            user.password_hash = hash_password(new_password)
        self._ensure_someone_can_manage_users(allow_no_staff=False)
        return user

    # --- roles ---------------------------------------------------------

    def list_roles(self) -> list[Role]:
        """Return all roles, the administrator first."""
        return self._roles.list_ordered()

    def get_role(self, role_id: int) -> Role | None:
        """Return the role with this id, or None."""
        return self._roles.get(role_id)

    def create_role(self, name_fa: str, name_en: str) -> Role:
        """Add a role with no access at all; the matrix then grants levels."""
        role = Role(key=self._new_role_key(name_en), name=name_fa.strip(), name_en=name_en.strip())
        return self._roles.add(role)

    def rename_role(self, role: Role, name_fa: str, name_en: str) -> Role:
        """Change the two names of a role. The administrator role keeps its names."""
        self._refuse_system_role(role)
        role.name = name_fa.strip()
        role.name_en = name_en.strip()
        return role

    def save_grants(self, role: Role, levels: Mapping[PermissionKey, AccessLevel]) -> Role:
        """Replace the role's levels with the matrix values; omitted permissions become 'none'.

        Raises SystemRoleError for the administrator and LockoutError if the change
        would leave nobody able to manage users.
        """
        self._refuse_system_role(role)
        existing = {grant.permission.key: grant for grant in role.grants}
        for permission in self._permissions.list_all():
            level = levels.get(PermissionKey(permission.key), AccessLevel.NONE)
            grant = existing.get(permission.key)
            if level is AccessLevel.NONE:
                if grant is not None:
                    role.grants.remove(grant)
            elif grant is not None:
                grant.access_level = level
            else:
                role.grants.append(RolePermission(permission=permission, access_level=level))
        self._ensure_someone_can_manage_users()
        return role

    def delete_role(self, role: Role) -> None:
        """Remove a role that nobody holds. Raises SystemRoleError or RoleInUseError."""
        self._refuse_system_role(role)
        if role.users:
            raise RoleInUseError(role.key)
        self._roles.delete(role)

    # --- rules ---------------------------------------------------------

    def _load_roles(self, role_ids: Collection[int]) -> list[Role]:
        """Return the roles with these ids; an unknown id raises UnknownRoleError."""
        roles = []
        for role_id in dict.fromkeys(role_ids):
            role = self._roles.get(role_id)
            if role is None:
                raise UnknownRoleError(str(role_id))
            roles.append(role)
        return roles

    @staticmethod
    def _refuse_system_role(role: Role) -> None:
        """Raise SystemRoleError when the role is the protected administrator role."""
        if role.is_system:
            raise SystemRoleError(role.key)

    def _ensure_someone_can_manage_users(self, allow_no_staff: bool = True) -> None:
        """Raise LockoutError unless an active user can still edit users and roles.

        Changing a role before any account exists locks nobody out, so that check
        passes; removing someone's last role must never leave the panel without staff.
        """
        staff = self._users.list_staff()
        if not staff and allow_no_staff:
            return
        if not any(self._access.build_profile(u).can_edit(PermissionKey.USERS) for u in staff):
            raise LockoutError("Nobody would be able to manage users")

    def _new_role_key(self, name_en: str) -> str:
        """Make a unique key from the English name, or a random one when it has no letters."""
        base = re.sub(r"[^a-z0-9]+", "-", name_en.lower()).strip("-")[:MAX_KEY_LENGTH]
        key = base or f"role-{secrets.token_hex(KEY_SUFFIX_BYTES)}"
        while self._roles.get_by_key(key) is not None:
            key = f"{base or 'role'}-{secrets.token_hex(KEY_SUFFIX_BYTES)}"
        return key
