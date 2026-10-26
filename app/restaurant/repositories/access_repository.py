"""Queries for users, roles and permissions."""

from sqlalchemy import func, or_, select
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

    def get_by_phone(self, phone: str) -> User | None:
        """Return the user with this phone number (already normalized), or None."""
        return self._session.scalar(select(User).where(User.phone == phone))

    def list_customers(self, text: str, offset: int, limit: int) -> tuple[list[User], int]:
        """Return one page of customers (users without a role, newest first) and the total.

        `text` narrows the list by name, phone or e-mail; an empty text keeps everyone.
        """
        conditions = [~User.roles.any(), User.registration_pending.is_(False)]
        text = text.strip()
        if text:
            like = f"%{text}%"
            conditions.append(
                or_(User.display_name.like(like), User.phone.like(like), User.email.like(like))
            )
        total = self._session.scalar(select(func.count(User.id)).where(*conditions)) or 0
        statement = (
            select(User).where(*conditions).order_by(User.id.desc()).offset(offset).limit(limit)
        )
        return list(self._session.scalars(statement)), total

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
