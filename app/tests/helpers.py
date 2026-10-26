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


def add_builder(key: str = "sandwich", kind: str = "sandwich", **fields):
    """Create a small sandwich-like builder and return it (ids are available after the flush).

    Steps: bread (one, required), layers (several, ordered, optional), sauce (one, required).
    """
    from restaurant.constants import PreviewKind
    from restaurant.models import (
        Builder,
        BuilderOption,
        BuilderOptionTranslation,
        BuilderStep,
        BuilderStepTranslation,
        BuilderTranslation,
    )

    def option(option_key, fa, en, price, **extra):
        return BuilderOption(
            key=option_key,
            price=price,
            translations=[
                BuilderOptionTranslation(language_id=language_id("fa"), name=fa),
                BuilderOptionTranslation(language_id=language_id("en"), name=en),
            ],
            **extra,
        )

    def step(step_key, fa, en, options, **extra):
        return BuilderStep(
            key=step_key,
            translations=[
                BuilderStepTranslation(language_id=language_id("fa"), title=fa),
                BuilderStepTranslation(language_id=language_id("en"), title=en),
            ],
            options=options,
            **extra,
        )

    builder = Builder(
        key=key,
        preview_kind=PreviewKind(kind),
        translations=[
            BuilderTranslation(language_id=language_id("fa"), name="ساندویچ دلخواه"),
            BuilderTranslation(language_id=language_id("en"), name="Custom sandwich"),
        ],
        steps=[
            step(
                "bread",
                "نان",
                "Bread",
                [
                    option("baguette", "باگت", "Baguette", 60_000, sort_order=0),
                    option("toast", "نان تست", "Toast", 50_000, sort_order=1),
                ],
                sort_order=0,
                is_base=True,
                preview_role="bread",
            ),
            step(
                "layers",
                "لایه‌ها",
                "Layers",
                [
                    option("cheese", "پنیر", "Cheese", 20_000, sort_order=0),
                    option("tomato", "گوجه", "Tomato", 10_000, sort_order=1),
                    option("lettuce", "کاهو", "Lettuce", 0, sort_order=2),
                    option("steak", "استیک", "Steak", 45_000, sort_order=3),
                ],
                sort_order=1,
                is_multiple=True,
                is_required=False,
                is_layered=True,
                preview_role="layer",
            ),
            step(
                "sauce",
                "سس",
                "Sauce",
                [
                    option("mayo", "مایونز", "Mayo", 0, sort_order=0),
                    option("ketchup", "کچاپ", "Ketchup", 0, sort_order=1),
                ],
                sort_order=2,
            ),
        ],
        **fields,
    )
    db.session.add(builder)
    db.session.flush()
    return builder


def option_ids(builder, *keys: str) -> list[int]:
    """Return the ids of the options with these keys, in the order the keys are given."""
    found = {option.key: option.id for step in builder.steps for option in step.options}
    return [found[key] for key in keys]


def add_tables(*capacities: int):
    """Create active tables labelled "1", "2"... with these capacities and return them."""
    from restaurant.models import DiningTable

    tables = [
        DiningTable(label=str(number), capacity=capacity, sort_order=number)
        for number, capacity in enumerate(capacities, start=1)
    ]
    db.session.add_all(tables)
    db.session.flush()
    return tables


CUSTOMER_PASSWORD = "customer-pass-1"
DEMO_CODE = "12345"


def make_customer(
    phone: str = "09121234567",
    name: str = "Sara Customer",
    email: str | None = None,
    password: str = CUSTOMER_PASSWORD,
    **fields,
):
    """Create a verified customer account (no role) and return it."""
    from restaurant.models import User
    from restaurant.services.auth_service import hash_password

    user = User(
        phone=phone,
        email=email,
        display_name=name,
        password_hash=hash_password(password),
        **fields,
    )
    db.session.add(user)
    db.session.commit()
    return user


def customer_sign_in(client, identifier: str, password: str = CUSTOMER_PASSWORD, lang: str = "fa"):
    """Post the public sign-in form and return the response."""
    return client.post(f"/{lang}/login", data={"identifier": identifier, "password": password})


def customer_client(app, **fields):
    """Return (client, user): a client signed in as a new customer."""
    user = make_customer(**fields)
    client = app.test_client()
    customer_sign_in(client, user.phone)
    return client, user


def register(client, lang: str = "fa", **overrides):
    """Post the registration form with valid values (override any of them)."""
    data = {
        "customer_name": "Sara Customer",
        "phone": "09121234567",
        "email": "",
        "password": CUSTOMER_PASSWORD,
        "password_again": CUSTOMER_PASSWORD,
        **overrides,
    }
    return client.post(f"/{lang}/register", data=data)
