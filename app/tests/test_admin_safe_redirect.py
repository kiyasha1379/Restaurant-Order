"""The `next` address after sign-in may only point at the panel itself (no open redirect)."""

import pytest

from restaurant.blueprints.admin.guards import safe_admin_target


@pytest.mark.parametrize(
    "target",
    [
        None,
        "",
        "https://evil.example/admin/",
        "http://evil.example",
        "//evil.example/admin/",
        "/\\evil.example",
        "/admin/\\evil.example",
        "javascript:alert(1)",
        "/admin",
        "/administrator/",
        "/fa/menu",
        "/admin/dash\nboard",
        "/admin/dash\tboard",
        "admin/dashboard",
    ],
)
def test_unsafe_next_is_refused(target):
    assert safe_admin_target(target) is None


@pytest.mark.parametrize(
    "target",
    [
        "/admin/dashboard",
        "/admin/orders?status=new",
        "/admin/orders/5#notes",
    ],
)
def test_panel_addresses_are_kept(target):
    assert safe_admin_target(target) == target
