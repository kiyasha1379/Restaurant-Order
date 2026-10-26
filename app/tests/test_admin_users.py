"""The users and roles section: staff accounts, roles, the permission matrix and lockout rules."""

import pytest

from restaurant.constants import AccessLevel, PermissionKey
from restaurant.extensions import db
from restaurant.models import Role, User
from tests.helpers import STAFF_PASSWORD, make_staff, sign_in, staff_client


def role(key: str) -> Role:
    return db.session.query(Role).filter_by(key=key).one()


def user(email: str) -> User:
    return db.session.query(User).filter_by(email=email).one()


@pytest.fixture
def admin_client(app):
    return staff_client(app, "admin")


def new_staff_data(**changes) -> dict:
    data = {
        "email": "new.person@example.com",
        "display_name": "New Person",
        "password": "long-enough-1",
        "role_ids": [],
        "is_active": "y",
    }
    return data | changes


def test_staff_list_shows_roles_and_status(admin_client) -> None:
    make_staff("cashier", is_active=False)
    page = admin_client.get("/admin/users").get_data(as_text=True)
    assert "admin@example.com" in page and "cashier@example.com" in page
    assert "مسدود" in page and "مدیر کل" in page


def test_create_staff_account_who_can_then_sign_in(app, admin_client) -> None:
    make_staff("kitchen")  # make sure the default roles exist
    data = new_staff_data(role_ids=[role("cashier").id])
    response = admin_client.post("/admin/users/new", data=data)
    assert response.status_code == 302
    created = user("new.person@example.com")
    assert [r.key for r in created.roles] == ["cashier"] and created.is_active
    assert sign_in(app.test_client(), "new.person@example.com", "long-enough-1").status_code == 302


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"email": "not-an-email"}, "ایمیل معتبر"),
        ({"display_name": " "}, "نام را وارد کنید"),
        ({"password": "short"}, "۸ نویسه"),
        ({"role_ids": []}, "دست‌کم یک نقش"),
    ],
)
def test_invalid_staff_form_is_refused(app, admin_client, changes, message) -> None:
    data = new_staff_data(role_ids=[role("admin").id]) | changes
    page = admin_client.post("/admin/users/new", data=data).get_data(as_text=True)
    assert message in page
    assert db.session.query(User).filter_by(email="new.person@example.com").count() == 0


def test_duplicate_email_is_refused(admin_client) -> None:
    data = new_staff_data(email="Admin@Example.com", role_ids=[role("admin").id])
    page = admin_client.post("/admin/users/new", data=data).get_data(as_text=True)
    assert "قبلاً ثبت شده" in page


def test_edit_staff_changes_name_roles_and_password(app, admin_client) -> None:
    cashier = make_staff("cashier")
    response = admin_client.post(
        f"/admin/users/{cashier.id}",
        data={
            "display_name": "Renamed",
            "password": "brand-new-pass-1",
            "role_ids": [role("kitchen").id, role("viewer").id],
            "is_active": "y",
        },
    )
    assert response.status_code == 302
    db.session.refresh(cashier)
    assert cashier.display_name == "Renamed"
    assert {r.key for r in cashier.roles} == {"kitchen", "viewer"}
    assert sign_in(app.test_client(), cashier.email, "brand-new-pass-1").status_code == 302


def test_blank_password_keeps_the_old_one(app, admin_client) -> None:
    cashier = make_staff("cashier")
    admin_client.post(
        f"/admin/users/{cashier.id}",
        data={
            "display_name": "Same",
            "password": "",
            "role_ids": [role("cashier").id],
            "is_active": "y",
        },
    )
    db.session.refresh(cashier)
    assert cashier.display_name == "Same" and cashier.is_active
    assert sign_in(app.test_client(), cashier.email, STAFF_PASSWORD).status_code == 302


def test_blocked_user_cannot_sign_in(app, admin_client) -> None:
    cashier = make_staff("cashier")
    client = app.test_client()
    assert sign_in(client, cashier.email).status_code == 302
    admin_client.post(  # the checkbox is left off: the account gets blocked
        f"/admin/users/{cashier.id}",
        data={"display_name": "Cashier", "role_ids": [role("cashier").id]},
    )
    db.session.refresh(cashier)
    assert not cashier.is_active
    assert client.get("/admin/orders").status_code == 302  # the open session is dead too
    fresh = app.test_client()
    response = sign_in(fresh, cashier.email)
    assert response.status_code == 200 and "مسدود" in response.get_data(as_text=True)


def test_staff_cannot_block_themselves(admin_client) -> None:
    me = user("admin@example.com")
    page = admin_client.post(
        f"/admin/users/{me.id}", data={"display_name": "Me", "role_ids": [role("admin").id]}
    ).get_data(as_text=True)
    assert "حساب خودتان را مسدود" in page
    assert user("admin@example.com").is_active


def test_last_user_manager_cannot_lose_the_role(admin_client) -> None:
    me = user("admin@example.com")
    page = admin_client.post(
        f"/admin/users/{me.id}",
        data={"display_name": "Me", "role_ids": [role("viewer").id], "is_active": "y"},
    ).get_data(as_text=True)
    assert "هیچ‌کس نتواند کاربران" in page
    assert [r.key for r in user("admin@example.com").roles] == ["admin"]


def test_editing_an_unknown_or_non_staff_account_is_404(admin_client) -> None:
    assert admin_client.get("/admin/users/9999").status_code == 404
    customer = User(email="customer@example.com", display_name="Customer")
    db.session.add(customer)
    db.session.commit()
    assert admin_client.get(f"/admin/users/{customer.id}").status_code == 404


def test_roles_list_and_system_role_is_read_only(admin_client) -> None:
    page = admin_client.get("/admin/users/roles").get_data(as_text=True)
    assert "سیستمی" in page and "دسترسی کامل" in page
    admin_role = role("admin")
    form = admin_client.get(f"/admin/users/roles/{admin_role.id}").get_data(as_text=True)
    assert "disabled" in form and "همیشه دسترسی کامل" in form
    response = admin_client.post(
        f"/admin/users/roles/{admin_role.id}", data={"name_fa": "هک", "name_en": "Hack"}
    )
    assert response.status_code == 302
    assert role("admin").name == "مدیر کل"
    assert admin_client.post(f"/admin/users/roles/{admin_role.id}/delete").status_code == 302
    assert db.session.query(Role).filter_by(key="admin").count() == 1


def test_create_role_with_matrix_and_assign_it(app, admin_client) -> None:
    response = admin_client.post(
        "/admin/users/roles/new",
        data={
            "name_fa": "پیشخدمت",
            "name_en": "Waiter",
            "level:orders": "edit",
            "level:menu": "view",
            "level:money": "view",
            "level:users": "bogus",
            "level:dash": "edit",
        },
    )
    assert response.status_code == 302
    waiter = role("waiter")
    levels = {g.permission.key: g.access_level for g in waiter.grants}
    assert levels == {
        "orders": AccessLevel.EDIT,
        "menu": AccessLevel.VIEW,
        "money": AccessLevel.VIEW,
        "dash": AccessLevel.EDIT,
    }
    admin_client.post("/admin/users/new", data=new_staff_data(role_ids=[waiter.id]))
    client = app.test_client()
    sign_in(client, "new.person@example.com", "long-enough-1")
    assert client.get("/admin/orders").status_code == 200
    assert client.get("/admin/menu").status_code == 200
    assert client.get("/admin/languages").status_code == 403


def test_money_cannot_be_edit_level_in_the_matrix(admin_client) -> None:
    admin_client.post(
        "/admin/users/roles/new",
        data={"name_fa": "الف", "name_en": "A", "level:money": "edit", "level:orders": "view"},
    )
    levels = {g.permission.key: g.access_level for g in role("a").grants}
    assert "money" not in levels or levels["money"] is AccessLevel.NONE


def test_saving_the_matrix_replaces_old_levels(admin_client) -> None:
    make_staff("cashier")
    cashier = role("cashier")
    admin_client.post(
        f"/admin/users/roles/{cashier.id}",
        data={"name_fa": "صندوقدار", "name_en": "Cashier", "level:orders": "view"},
    )
    db.session.refresh(cashier)
    assert {g.permission.key: g.access_level for g in cashier.grants} == {
        "orders": AccessLevel.VIEW
    }


def test_role_names_are_validated(admin_client) -> None:
    page = admin_client.post("/admin/users/roles/new", data={"name_fa": "", "name_en": "X"})
    assert "نام فارسی نقش لازم است" in page.get_data(as_text=True)
    assert db.session.query(Role).filter_by(key="x").count() == 0


def test_role_with_users_cannot_be_deleted_but_an_empty_one_can(admin_client) -> None:
    make_staff("cashier")
    cashier = role("cashier")
    assert admin_client.post(f"/admin/users/roles/{cashier.id}/delete").status_code == 302
    assert db.session.query(Role).filter_by(key="cashier").count() == 1
    kitchen_free = role("kitchen")
    assert not kitchen_free.users
    admin_client.post(f"/admin/users/roles/{kitchen_free.id}/delete")
    assert db.session.query(Role).filter_by(key="kitchen").count() == 0


def test_matrix_change_that_locks_everybody_out_is_refused(app) -> None:
    from restaurant.constants import AccessLevel
    from restaurant.service_factory import make_access_service, make_staff_service

    make_access_service().ensure_defaults()
    service = make_staff_service()
    boss = service.create_role("رئیس", "Boss")
    service.save_grants(boss, {PermissionKey.USERS: AccessLevel.EDIT})
    service.create_staff("boss@example.com", "Boss", STAFF_PASSWORD, [boss.id])
    db.session.commit()
    client = app.test_client()
    sign_in(client, "boss@example.com")
    response = client.post(
        f"/admin/users/roles/{boss.id}",
        data={"name_fa": "رئیس", "name_en": "Boss", "level:users": "view"},
        follow_redirects=True,
    )
    assert "هیچ‌کس نتواند کاربران" in response.get_data(as_text=True)
    db.session.expire_all()
    levels = {g.permission.key: g.access_level for g in role("boss").grants}
    assert levels == {"users": AccessLevel.EDIT}


def test_view_only_access_cannot_change_anything(app) -> None:
    client = staff_client(app, "viewer")
    assert client.get("/admin/users").status_code == 200
    page = client.get("/admin/users/new")
    assert page.status_code == 403
    me = user("viewer@example.com")
    assert client.get(f"/admin/users/{me.id}").status_code == 200
    assert client.post(f"/admin/users/{me.id}", data={"display_name": "x"}).status_code == 403
    assert client.post("/admin/users/roles/new", data={"name_fa": "ب"}).status_code == 403
    assert client.post(f"/admin/users/roles/{role('viewer').id}/delete").status_code == 403


def test_roles_without_the_permission_are_refused(app) -> None:
    assert staff_client(app, "manager").get("/admin/users").status_code == 403
    assert staff_client(app, "cashier").get("/admin/users/roles").status_code == 403


def test_users_section_appears_in_the_sidebar_only_with_permission(app) -> None:
    assert "/admin/users" in staff_client(app, "admin").get("/admin/dashboard").get_data(
        as_text=True
    )
    page = staff_client(app, "manager").get("/admin/dashboard").get_data(as_text=True)
    assert 'href="/admin/users"' not in page


def test_anonymous_visitors_are_sent_to_sign_in(app) -> None:
    response = app.test_client().get("/admin/users")
    assert response.status_code == 302 and "/admin/login" in response.headers["Location"]


def test_matrix_has_every_permission_and_english_panel_text(admin_client) -> None:
    admin_client.get("/admin/language/en")
    page = admin_client.get("/admin/users/roles/new").get_data(as_text=True)
    assert page.count('type="radio"') == 10 * 3 + 2
    assert "Permission matrix" in page and "See money and customer details" in page


def test_csrf_is_enforced_on_user_forms() -> None:
    from restaurant import create_app

    app = create_app("test", {"WTF_CSRF_ENABLED": True})
    client = app.test_client()
    assert client.post("/admin/users/new", data=new_staff_data()).status_code == 400
    assert client.post("/admin/users/roles/1/delete").status_code == 400
