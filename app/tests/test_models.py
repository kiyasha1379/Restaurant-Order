"""Database rules that live in the schema itself."""

import pytest
from sqlalchemy.exc import IntegrityError

from restaurant.constants import AccessLevel, TextDirection
from restaurant.extensions import db
from restaurant.models import (
    Background,
    Category,
    CategoryTranslation,
    Dish,
    Language,
    Permission,
    Role,
    RolePermission,
    Setting,
    User,
)


def test_a_third_language_is_rejected(app):
    db.session.add(Language(code="de", name="Deutsch", direction=TextDirection.LTR))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_background_dim_must_be_between_zero_and_one(app):
    db.session.add(Background(key="home-hero", dim=1.5))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_background_defaults(app):
    db.session.add(Background(key="menu-page"))
    db.session.commit()
    background = db.session.query(Background).one()
    assert background.mobile_mode.value == "poster_only"
    assert background.is_enabled is True
    assert background.dim == pytest.approx(0.45)


def test_dish_price_cannot_be_negative(app):
    category = Category(slug="pizza")
    db.session.add(category)
    db.session.flush()
    db.session.add(Dish(category_id=category.id, base_price=-1))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_foreign_keys_are_enforced(app):
    db.session.add(Dish(category_id=999, base_price=10))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_one_translation_per_language(app):
    category = Category(slug="drinks")
    db.session.add(category)
    db.session.flush()
    persian_id = db.session.query(Language).filter_by(code="fa").one().id
    db.session.add(
        CategoryTranslation(category_id=category.id, language_id=persian_id, name="نوشیدنی")
    )
    db.session.add(
        CategoryTranslation(category_id=category.id, language_id=persian_id, name="دوباره")
    )
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_user_roles_and_permission_levels(app):
    permission = Permission(key="orders")
    role = Role(key="cashier", name="Cashier")
    role.grants.append(RolePermission(permission=permission, access_level=AccessLevel.EDIT))
    user = User(email="staff@example.com", display_name="Staff", roles=[role])
    db.session.add(user)
    db.session.commit()

    stored_user = db.session.query(User).one()
    grant = stored_user.roles[0].grants[0]
    assert grant.permission.key == "orders"
    assert grant.access_level is AccessLevel.EDIT


def test_setting_primary_key_is_its_name(app):
    db.session.add(Setting(key="brand_name", value="Saffron"))
    db.session.commit()
    assert db.session.get(Setting, "brand_name").value == "Saffron"
