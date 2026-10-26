"""Users and access: users, roles, permissions and how they connect."""

from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Column, ForeignKey, String, Table, Text, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from restaurant.constants import AccessLevel
from restaurant.extensions import db
from restaurant.models.columns import enum_type
from restaurant.models.mixins import TimestampMixin

# A user can hold several roles; a role belongs to many users.
user_roles = Table(
    "user_roles",
    db.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class User(UserMixin, TimestampMixin, db.Model):
    """A staff member or an (optional) customer account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120), default="")
    is_active: Mapped[bool] = mapped_column(default=True)
    last_login_at: Mapped[datetime | None] = mapped_column()
    # A customer who registered but has not yet typed the verification code cannot sign in.
    registration_pending: Mapped[bool] = mapped_column(default=False, server_default=false())
    # The customer's cart as JSON, so it follows the account to another device.
    saved_cart: Mapped[str | None] = mapped_column(Text)

    roles: Mapped[list["Role"]] = relationship(secondary=user_roles, back_populates="users")
    addresses: Mapped[list["Address"]] = relationship(  # noqa: F821 - defined in customer.py
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="(Address.is_default.desc(), Address.id)",
    )


class Role(db.Model):
    """A named bundle of permissions, edited in the admin permission matrix."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    name_en: Mapped[str] = mapped_column(String(80), default="")
    # A system role (the administrator) cannot be edited or deleted, so nobody gets locked out.
    is_system: Mapped[bool] = mapped_column(default=False)

    users: Mapped[list[User]] = relationship(secondary=user_roles, back_populates="roles")
    grants: Mapped[list["RolePermission"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )

    def name_in(self, language_code: str) -> str:
        """Return the role name in a language, falling back to the Persian name."""
        return (self.name_en if language_code == "en" else self.name) or self.name


class Permission(db.Model):
    """One admin section (dash, orders, menu...) or the separate 'money' permission."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True)


class RolePermission(db.Model):
    """The access level one role has on one permission."""

    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"))
    access_level: Mapped[AccessLevel] = mapped_column(
        enum_type(AccessLevel), default=AccessLevel.NONE
    )

    role: Mapped[Role] = relationship(back_populates="grants")
    permission: Mapped[Permission] = relationship()
