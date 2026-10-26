"""Access profiles, default roles, sign-in checks and staff management."""

import pytest

from restaurant.constants import AccessLevel, PermissionKey
from restaurant.extensions import db
from restaurant.models import Permission, Role, User
from restaurant.service_factory import (
    make_access_service,
    make_auth_service,
    make_staff_service,
)
from restaurant.services import (
    DuplicateEmailError,
    LockoutError,
    LoginOutcome,
    RoleInUseError,
    SystemRoleError,
    UnknownRoleError,
    WeakPasswordError,
)

PASSWORD = "correct-horse-1"


@pytest.fixture
def roles(app) -> dict[str, Role]:
    """The default roles, created the way `flask create-admin` does."""
    make_access_service().ensure_defaults()
    db.session.commit()
    return {role.key: role for role in db.session.query(Role)}


def make_user(role: Role | None, email: str = "staff@example.com", **fields) -> User:
    staff = make_staff_service()
    user = staff.create_staff(email, "Staff", PASSWORD, [role.id] if role else [])
    for name, value in fields.items():
        setattr(user, name, value)
    db.session.commit()
    return user


def test_ensure_defaults_creates_permissions_and_roles_once(app) -> None:
    first = make_access_service().ensure_defaults()
    db.session.commit()
    second = make_access_service().ensure_defaults()
    assert first == len(PermissionKey) + 5
    assert second == 0
    assert db.session.query(Permission).count() == len(PermissionKey)


def test_ensure_defaults_never_changes_an_edited_role(app, roles) -> None:
    kitchen = roles["kitchen"]
    kitchen.name = "Chefs"
    db.session.commit()
    make_access_service().ensure_defaults()
    db.session.commit()
    assert db.session.get(Role, kitchen.id).name == "Chefs"


def test_system_role_gets_a_permission_added_later(app, roles) -> None:
    admin = roles["admin"]
    admin.grants.clear()
    db.session.commit()
    make_access_service().ensure_defaults()
    db.session.commit()
    assert len(db.session.get(Role, admin.id).grants) == len(PermissionKey)


def test_cashier_sees_money_and_kitchen_does_not(app, roles) -> None:
    access = make_access_service()
    cashier = access.build_profile(make_user(roles["cashier"], "c@example.com"))
    kitchen = access.build_profile(make_user(roles["kitchen"], "k@example.com"))
    assert cashier.can_see_money and cashier.can_edit(PermissionKey.ORDERS)
    assert not kitchen.can_see_money
    assert kitchen.can_edit(PermissionKey.ORDERS)
    assert not kitchen.allows(PermissionKey.MENU)


def test_viewer_can_view_everything_but_change_nothing(app, roles) -> None:
    viewer = make_access_service().build_profile(make_user(roles["viewer"]))
    assert all(viewer.allows(key) for key in PermissionKey)
    assert not any(viewer.can_edit(key) for key in PermissionKey)


def test_highest_level_of_several_roles_wins(app, roles) -> None:
    staff = make_staff_service()
    user = staff.create_staff(
        "both@example.com", "Both", PASSWORD, [roles["viewer"].id, roles["kitchen"].id]
    )
    profile = make_access_service().build_profile(user)
    assert profile.level(PermissionKey.ORDERS) is AccessLevel.EDIT
    assert profile.level(PermissionKey.MENU) is AccessLevel.VIEW


def test_blocked_user_has_no_access(app, roles) -> None:
    user = make_user(roles["admin"], is_active=False)
    assert not make_access_service().build_profile(user).has_admin_access


def test_system_role_is_full_access_even_without_grants(app, roles) -> None:
    roles["admin"].grants.clear()
    user = make_user(roles["admin"])
    profile = make_access_service().build_profile(user)
    assert all(profile.can_edit(key) for key in PermissionKey)


def test_authenticate_outcomes(app, roles) -> None:
    make_user(roles["cashier"], "ok@example.com")
    make_user(roles["cashier"], "blocked@example.com", is_active=False)
    make_user(None, "customer@example.com")
    auth = make_auth_service()
    assert auth.authenticate("OK@example.com ", PASSWORD).outcome is LoginOutcome.OK
    assert auth.authenticate("ok@example.com", "wrong").outcome is LoginOutcome.INVALID
    assert auth.authenticate("nobody@example.com", PASSWORD).outcome is LoginOutcome.INVALID
    assert auth.authenticate("blocked@example.com", PASSWORD).outcome is LoginOutcome.BLOCKED
    assert auth.authenticate("customer@example.com", PASSWORD).outcome is LoginOutcome.NO_ACCESS
    assert auth.authenticate("blocked@example.com", "wrong").outcome is LoginOutcome.INVALID


def test_successful_login_records_the_time(app, roles) -> None:
    user = make_user(roles["cashier"], "t@example.com")
    assert user.last_login_at is None
    make_auth_service().authenticate("t@example.com", PASSWORD)
    assert user.last_login_at is not None


def test_passwords_are_stored_hashed(app, roles) -> None:
    user = make_user(roles["cashier"])
    assert user.password_hash and PASSWORD not in user.password_hash
    assert user.password_hash.startswith("scrypt:")


def test_create_staff_rules(app, roles) -> None:
    staff = make_staff_service()
    make_user(roles["cashier"], "dup@example.com")
    with pytest.raises(DuplicateEmailError):
        staff.create_staff("DUP@example.com", "X", PASSWORD, [])
    with pytest.raises(WeakPasswordError):
        staff.create_staff("new@example.com", "X", "short", [])
    with pytest.raises(UnknownRoleError):
        staff.create_staff("new@example.com", "X", PASSWORD, [9999])


def test_last_administrator_cannot_be_blocked_or_demoted(app, roles) -> None:
    admin = make_user(roles["admin"], "admin@example.com")
    staff = make_staff_service()
    with pytest.raises(LockoutError):
        staff.update_staff(admin, "Admin", [roles["admin"].id], is_active=False)
    db.session.rollback()
    with pytest.raises(LockoutError):
        staff.update_staff(admin, "Admin", [roles["cashier"].id], is_active=True)
    db.session.rollback()
    with pytest.raises(LockoutError):
        staff.update_staff(admin, "Admin", [], is_active=True)
    db.session.rollback()
    second = make_user(roles["admin"], "second@example.com")
    staff.update_staff(second, "Second", [roles["cashier"].id], is_active=True)
    assert second.roles == [roles["cashier"]]


def test_role_matrix_and_protection(app, roles) -> None:
    staff = make_staff_service()
    role = staff.create_role("تست", "Test role")
    assert role.key == "test-role"
    staff.save_grants(
        role, {PermissionKey.MENU: AccessLevel.EDIT, PermissionKey.ORDERS: AccessLevel.VIEW}
    )
    db.session.commit()
    levels = {g.permission.key: g.access_level for g in role.grants}
    assert levels == {"menu": AccessLevel.EDIT, "orders": AccessLevel.VIEW}
    staff.save_grants(role, {PermissionKey.MENU: AccessLevel.VIEW})
    db.session.commit()
    assert {g.permission.key: g.access_level for g in role.grants} == {"menu": AccessLevel.VIEW}
    with pytest.raises(SystemRoleError):
        staff.save_grants(roles["admin"], {})
    with pytest.raises(SystemRoleError):
        staff.delete_role(roles["admin"])


def test_a_role_with_users_cannot_be_deleted(app, roles) -> None:
    make_user(roles["cashier"])
    with pytest.raises(RoleInUseError):
        make_staff_service().delete_role(roles["cashier"])
    unused = roles["viewer"]
    make_staff_service().delete_role(unused)
    db.session.commit()
    assert db.session.query(Role).filter_by(key="viewer").count() == 0


def test_removing_users_edit_from_the_only_manager_role_is_refused(app, roles) -> None:
    staff = make_staff_service()
    role = staff.create_role("مدیر کاربران", "Users manager")
    staff.save_grants(role, {PermissionKey.USERS: AccessLevel.EDIT})
    db.session.commit()
    make_user(role, "um@example.com")
    with pytest.raises(LockoutError):
        staff.save_grants(role, {PermissionKey.USERS: AccessLevel.VIEW})
    db.session.rollback()
