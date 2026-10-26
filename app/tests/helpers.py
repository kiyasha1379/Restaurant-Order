"""Helpers that build menu rows for tests."""

from restaurant.extensions import db
from restaurant.models import Category, CategoryTranslation, Dish, DishTranslation, Language


def language_id(code: str) -> int:
    return db.session.query(Language).filter_by(code=code).one().id


def add_category(slug: str, names: dict[str, str], **fields) -> Category:
    category = Category(
        slug=slug,
        translations=[
            CategoryTranslation(language_id=language_id(code), name=name)
            for code, name in names.items()
        ],
        **fields,
    )
    db.session.add(category)
    db.session.flush()
    return category


def add_dish(category: Category, names: dict[str, str], **fields) -> Dish:
    dish = Dish(
        category=category,
        translations=[
            DishTranslation(language_id=language_id(code), name=name, description=f"d-{code}")
            for code, name in names.items()
        ],
        **fields,
    )
    db.session.add(dish)
    db.session.flush()
    return dish


STAFF_PASSWORD = "staff-password-1"


def make_staff(role_key: str, email: str | None = None, **fields):
    """Create a staff account holding one default role (the roles are created if missing)."""
    from restaurant.service_factory import make_access_service, make_staff_service

    make_access_service().ensure_defaults()
    db.session.flush()
    from restaurant.models import Role

    role = db.session.query(Role).filter_by(key=role_key).one()
    user = make_staff_service().create_staff(
        email or f"{role_key}@example.com", role_key.title(), STAFF_PASSWORD, [role.id]
    )
    for name, value in fields.items():
        setattr(user, name, value)
    db.session.commit()
    return user


def sign_in(client, email: str, password: str = STAFF_PASSWORD):
    """Post the sign-in form and return the response (cookies stay in the client)."""
    return client.post("/admin/login", data={"email": email, "password": password})


def staff_client(app, role_key: str):
    """Return a test client already signed in as a new staff member with this role."""
    user = make_staff(role_key)
    client = app.test_client()
    sign_in(client, user.email)
    return client


def make_image_bytes(
    image_format: str = "PNG", size: tuple[int, int] = (400, 300), mode="RGB"
) -> bytes:
    """Return a small valid picture of the given format, for upload tests."""
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new(mode, size, (200, 120, 60) if mode == "RGB" else 128).save(
        buffer, format=image_format
    )
    return buffer.getvalue()
