"""Queries for users, roles and permissions."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from restaurant.models import Permission, Role, RolePermission, User
from restaurant.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Reads and stores users."""

    model = User

    def get_by_email(self, email: str) -> User | None:
        """Return the user with this e-mail address (case does not matter), or None."""
        return self._session.scalar(select(User).where(User.email == email.strip().lower()))

    def list_staff(self) -> list[User]:
        """Return every user who holds at least one role, with roles and grants loaded."""
        statement = (
            select(User)
            .where(User.roles.any())
            .options(
                selectinload(User.roles)
                .selectinload(Role.grants)
                .selectinload(RolePermission.permission)
            )
            .order_by(User.id)
        )
        return list(self._session.scalars(statement))

    def delete(self, user: User) -> None:
        """Stage the removal of a user. The caller commits."""
        self._session.delete(user)


class RoleRepository(BaseRepository[Role]):
    """Reads and stores roles with their grants."""

    model = Role

    def list_ordered(self) -> list[Role]:
        """Return all roles, the system role first, with grants and permissions loaded."""
        statement = (
            select(Role)
            .options(
                selectinload(Role.grants).selectinload(RolePermission.permission),
                selectinload(Role.users),
            )
            .order_by(Role.is_system.desc(), Role.id)
        )
        return list(self._session.scalars(statement))

    def get_by_key(self, key: str) -> Role | None:
        """Return the role with this key, or None."""
        return self._session.scalar(select(Role).where(Role.key == key))

    def delete(self, role: Role) -> None:
        """Stage the removal of a role. The caller commits."""
        self._session.delete(role)


class PermissionRepository(BaseRepository[Permission]):
    """Reads the fixed list of permissions."""

    model = Permission

    def list_ordered(self) -> list[Permission]:
        """Return the permissions in creation order."""
        return list(self._session.scalars(select(Permission).order_by(Permission.id)))
