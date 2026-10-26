"""Who may do what: access profiles of users and the default roles."""

from collections.abc import Mapping
from dataclasses import dataclass

from restaurant.access_defaults import DEFAULT_ROLES
from restaurant.constants import AccessLevel, PermissionKey
from restaurant.models import Permission, Role, RolePermission, User
from restaurant.repositories import PermissionRepository, RoleRepository

SECTION_KEYS = tuple(key for key in PermissionKey if key is not PermissionKey.MONEY)


@dataclass(frozen=True)
class AccessProfile:
    """The level a user has on each permission. Missing keys mean 'none'."""

    levels: Mapping[PermissionKey, AccessLevel]

    def level(self, key: PermissionKey) -> AccessLevel:
        """Return the level on one permission."""
        return self.levels.get(key, AccessLevel.NONE)

    def allows(self, key: PermissionKey, required: AccessLevel = AccessLevel.VIEW) -> bool:
        """Return True when the level on `key` reaches `required`."""
        return self.level(key).allows(required)

    def can_edit(self, key: PermissionKey) -> bool:
        """Return True when the user may change things in this section."""
        return self.allows(key, AccessLevel.EDIT)

    @property
    def can_see_money(self) -> bool:
        """Amounts and customer details are shown only with the 'money' permission."""
        return self.allows(PermissionKey.MONEY, AccessLevel.VIEW)

    @property
    def has_admin_access(self) -> bool:
        """Return True when at least one admin section is open to the user."""
        return any(self.allows(key) for key in SECTION_KEYS)


NO_ACCESS = AccessProfile({})


class AccessService:
    """Works out access profiles and keeps the permission list and default roles in place."""

    def __init__(
        self, role_repository: RoleRepository, permission_repository: PermissionRepository
    ) -> None:
        """Receive the repositories instead of importing them, so tests can swap them."""
        self._role_repository = role_repository
        self._permission_repository = permission_repository

    @staticmethod
    def build_profile(user: User) -> AccessProfile:
        """Combine the grants of all the user's roles: the highest level on each permission.

        A blocked user has no access. A system role (the administrator) always
        has full access, even if its grants were damaged.
        """
        if not user.is_active:
            return NO_ACCESS
        levels: dict[PermissionKey, AccessLevel] = {}
        for role in user.roles:
            if role.is_system:
                return AccessProfile(dict.fromkeys(PermissionKey, AccessLevel.EDIT))
            for grant in role.grants:
                key = PermissionKey(grant.permission.key)
                if grant.access_level.rank > levels.get(key, AccessLevel.NONE).rank:
                    levels[key] = grant.access_level
        return AccessProfile(levels)

    def list_permissions(self) -> list[Permission]:
        """Return the permissions in a stable order."""
        return self._permission_repository.list_ordered()

    def ensure_defaults(self) -> int:
        """Create missing permissions and default roles; return how many rows were added.

        Existing roles keep what an administrator set. Only the system role is
        topped up, so a permission added by a later phase reaches the administrator.
        The caller commits.
        """
        added = 0
        permissions = {p.key: p for p in self._permission_repository.list_all()}
        for key in PermissionKey:
            if key.value not in permissions:
                permissions[key.value] = self._permission_repository.add(Permission(key=key.value))
                added += 1
        for default in DEFAULT_ROLES:
            role = self._role_repository.get_by_key(default.key)
            if role is None:
                role = self._role_repository.add(
                    Role(
                        key=default.key,
                        name=default.name_fa,
                        name_en=default.name_en,
                        is_system=default.is_system,
                    )
                )
                added += 1
                for key, level in default.grants.items():
                    role.grants.append(
                        RolePermission(permission=permissions[key.value], access_level=level)
                    )
            elif role.is_system:
                held = {grant.permission.key for grant in role.grants}
                for key, level in default.grants.items():
                    if key.value not in held:
                        role.grants.append(
                            RolePermission(permission=permissions[key.value], access_level=level)
                        )
        return added
