"""The menu section of the panel: dishes, photos, categories, view-only roles."""

from io import BytesIO
from pathlib import Path

import pytest

from restaurant.extensions import db
from restaurant.models import Category, Dish, Order, OrderItem
from tests.helpers import add_category, add_dish, make_image_bytes, staff_client


@pytest.fixture
def menu_data(app):
    pizza = add_category("pizza", {"fa": "پیتزا", "en": "Pizza"}, sort_order=0)
    drinks = add_category("drinks", {"fa": "نوشیدنی", "en": "Drinks"}, sort_order=1)
    margherita = add_dish(
        pizza, {"fa": "مارگاریتا", "en": "Margherita"}, base_price=250_000, sort_order=0
    )
    pepperoni = add_dish(pizza, {"fa": "پپرونی"}, base_price=300_000, sort_order=1)
    cola = add_dish(drinks, {"fa": "نوشابه", "en": "Cola"}, base_price=40_000, is_visible=False)
    db.session.commit()
    return {
        "pizza": pizza,
        "drinks": drinks,
        "margherita": margherita,
        "pepperoni": pepperoni,
        "cola": cola,
    }


def dish_form(category_id: int, **overrides) -> dict:
    data = {
        "category_id": category_id,
        "base_price": "120000",
        "sort_order": "0",
        "is_in_stock": "y",
        "is_visible": "y",
        "name_fa": "کباب کوبیده",
        "name_en": "Koobideh kebab",
        "description_fa": "با برنج",
        "description_en": "With rice",
        "ingredients_fa": "گوشت، پیاز",
        "ingredients_en": "Beef, onion",
        "serving_note_fa": "داغ",
        "serving_note_en": "Hot",
    }
    data.update(overrides)
    return {key: value for key, value in data.items() if value is not None}


def photo_field(name: str = "photo.png", data: bytes | None = None) -> tuple[BytesIO, str]:
    return BytesIO(data if data is not None else make_image_bytes()), name


def uploaded_files(app) -> list[Path]:
    root = Path(app.config["UPLOAD_FOLDER"])
    return sorted(root.rglob("*.webp")) if root.exists() else []


def test_list_shows_dishes_by_category_with_flags(app, menu_data) -> None:
    page = staff_client(app, "manager").get("/admin/menu").get_data(as_text=True)
    for text in ("مارگاریتا", "پپرونی", "نوشابه", "پیتزا", "نوشیدنی"):
        assert text in page
    assert page.count("بدون ترجمه‌ی انگلیسی") >= 2  # the filter chip and pepperoni's badge
    assert "مخفی" in page


def test_filters(app, menu_data) -> None:
    client = staff_client(app, "manager")
    by_category = client.get(f"/admin/menu?category={menu_data['drinks'].id}").get_data(
        as_text=True
    )
    assert "نوشابه" in by_category and "مارگاریتا" not in by_category
    missing = client.get("/admin/menu?missing=en").get_data(as_text=True)
    assert "پپرونی" in missing and "مارگاریتا" not in missing


def test_stock_and_visibility_toggles(app, menu_data) -> None:
    client = staff_client(app, "manager")
    dish = menu_data["margherita"]
    client.post(f"/admin/menu/dishes/{dish.id}/stock", data={"value": "0"})
    client.post(f"/admin/menu/dishes/{dish.id}/visible", data={"value": "0"})
    db.session.refresh(dish)
    assert not dish.is_in_stock and not dish.is_visible
    client.post(f"/admin/menu/dishes/{dish.id}/stock", data={"value": "1"})
    db.session.refresh(dish)
    assert dish.is_in_stock


def test_move_dish_changes_order_even_when_all_orders_are_equal(app, menu_data) -> None:
    for dish in (menu_data["margherita"], menu_data["pepperoni"]):
        dish.sort_order = 0
    db.session.commit()
    client = staff_client(app, "manager")
    client.post(f"/admin/menu/dishes/{menu_data['pepperoni'].id}/move", data={"direction": "up"})
    page = client.get("/admin/menu").get_data(as_text=True)
    assert page.index("پپرونی") < page.index("مارگاریتا")
    assert (
        client.post(
            f"/admin/menu/dishes/{menu_data['pepperoni'].id}/move", data={"direction": "x"}
        ).status_code
        == 400
    )


def test_create_dish_with_both_languages_and_photo(app, menu_data) -> None:
    client = staff_client(app, "manager")
    response = client.post(
        "/admin/menu/dishes/new",
        data={**dish_form(menu_data["pizza"].id, base_price="۱۲۰٬۰۰۰"), "photo": photo_field()},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    dish = db.session.query(Dish).filter(Dish.base_price == 120_000).one()
    assert {row.language.code: row.name for row in dish.translations} == {
        "fa": "کباب کوبیده",
        "en": "Koobideh kebab",
    }
    assert dish.images and dish.images[0].path.startswith("uploads/dishes/")
    assert len(uploaded_files(app)) == 1
    assert client.get(response.headers["Location"]).status_code == 200


def test_english_text_is_optional_and_removable(app, menu_data) -> None:
    client = staff_client(app, "manager")
    dish = menu_data["margherita"]
    form = dish_form(
        dish.category_id, name_en="", description_en="", ingredients_en="", serving_note_en=""
    )
    assert client.post(f"/admin/menu/dishes/{dish.id}", data=form).status_code == 302
    db.session.refresh(dish)
    assert [row.language.code for row in dish.translations] == ["fa"]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"name_fa": "  "}, "نام را وارد کنید"),
        ({"base_price": "abc"}, "یک عدد صحیح وارد کنید"),
        ({"base_price": "-5"}, "یک عدد صحیح وارد کنید"),
        ({"base_price": "999999999999"}, "قیمت باید عددی"),
        ({"category_id": "999"}, "یکی از گزینه‌ها"),
        ({"description_fa": "x" * 1001}, "بیش از حد طولانی"),
    ],
)
def test_invalid_dish_forms_show_errors_and_save_nothing(
    app, menu_data, overrides, message
) -> None:
    client = staff_client(app, "manager")
    before = db.session.query(Dish).count()
    response = client.post(
        "/admin/menu/dishes/new", data={**dish_form(menu_data["pizza"].id), **overrides}
    )
    assert response.status_code == 200
    assert message in response.get_data(as_text=True)
    assert db.session.query(Dish).count() == before


def test_bad_photo_is_reported_and_the_dish_is_not_created(app, menu_data) -> None:
    client = staff_client(app, "manager")
    before = db.session.query(Dish).count()
    response = client.post(
        "/admin/menu/dishes/new",
        data={
            **dish_form(menu_data["pizza"].id),
            "photo": photo_field("evil.png", b"<svg onload=alert(1)>"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert "این فایل یک عکس سالم نیست" in response.get_data(as_text=True)
    assert db.session.query(Dish).count() == before
    assert uploaded_files(app) == []


def test_replacing_and_removing_a_photo_cleans_up_files(app, menu_data) -> None:
    client = staff_client(app, "manager")
    dish = menu_data["margherita"]
    url = f"/admin/menu/dishes/{dish.id}"
    client.post(
        url,
        data={**dish_form(dish.category_id), "photo": photo_field()},
        content_type="multipart/form-data",
    )
    first = uploaded_files(app)
    assert len(first) == 1
    client.post(
        url,
        data={**dish_form(dish.category_id), "photo": photo_field()},
        content_type="multipart/form-data",
    )
    second = uploaded_files(app)
    assert len(second) == 1 and second != first
    client.post(url, data={**dish_form(dish.category_id), "remove_photo": "y"})
    assert uploaded_files(app) == []
    db.session.refresh(dish)
    assert dish.images == []


def test_delete_dish_removes_it_and_its_photo_but_not_old_orders(app, menu_data) -> None:
    client = staff_client(app, "manager")
    dish = menu_data["margherita"]
    client.post(
        f"/admin/menu/dishes/{dish.id}",
        data={**dish_form(dish.category_id), "photo": photo_field()},
        content_type="multipart/form-data",
    )
    order = Order(
        public_token="t1",
        language_code="fa",
        customer_name="A",
        customer_phone="09120000000",
        fulfillment="takeaway",
        payment_method="cash_on_site",
        status="placed",
        subtotal=1,
        delivery_fee=0,
        total=1,
        items=[
            OrderItem(dish_id=dish.id, name_fa="مارگاریتا", unit_price=1, quantity=1, line_total=1)
        ],
    )
    db.session.add(order)
    db.session.commit()
    assert client.post(f"/admin/menu/dishes/{dish.id}/delete").status_code == 302
    assert db.session.get(Dish, dish.id) is None
    assert uploaded_files(app) == []
    item = db.session.query(OrderItem).one()
    assert item.name_fa == "مارگاریتا" and item.dish_id is None


def test_unknown_dish_is_404(app) -> None:
    client = staff_client(app, "manager")
    assert client.get("/admin/menu/dishes/999").status_code == 404
    assert client.post("/admin/menu/dishes/999").status_code == 404


def test_roles_without_menu_access_get_403_and_viewers_cannot_change(app, menu_data) -> None:
    kitchen = staff_client(app, "kitchen")
    assert kitchen.get("/admin/menu").status_code == 403
    assert kitchen.post(f"/admin/menu/dishes/{menu_data['margherita'].id}/stock").status_code == 403
    viewer = staff_client(app, "viewer")
    page = viewer.get("/admin/menu").get_data(as_text=True)
    assert "مارگاریتا" in page and "/stock" not in page and "افزودن غذا" not in page
    form_page = viewer.get(f"/admin/menu/dishes/{menu_data['margherita'].id}").get_data(
        as_text=True
    )
    assert "disabled" in form_page and 'type="submit"' not in form_page.split('<form class="form"')[
        1
    ].split("</form>")[0].replace("btn--primary", "")
    assert viewer.get("/admin/menu/dishes/new").status_code == 403
    assert (
        viewer.post("/admin/menu/dishes/new", data=dish_form(menu_data["pizza"].id)).status_code
        == 403
    )
    assert viewer.post(f"/admin/menu/dishes/{menu_data['margherita'].id}/delete").status_code == 403
    assert db.session.get(Dish, menu_data["margherita"].id) is not None


def test_changes_reach_the_public_menu(app, menu_data) -> None:
    client = staff_client(app, "manager")
    public = app.test_client()
    assert "مارگاریتا" in public.get("/fa/menu").get_data(as_text=True)
    client.post(f"/admin/menu/dishes/{menu_data['margherita'].id}/visible", data={"value": "0"})
    assert "مارگاریتا" not in public.get("/fa/menu").get_data(as_text=True)
    client.post(f"/admin/menu/dishes/{menu_data['cola'].id}/visible", data={"value": "1"})
    client.post(f"/admin/menu/dishes/{menu_data['cola'].id}/stock", data={"value": "0"})
    assert "ناموجود" in public.get("/fa/menu").get_data(as_text=True)


# --- categories ----------------------------------------------------------


def category_form(**overrides) -> dict:
    data = {
        "slug": "salads",
        "sort_order": "5",
        "is_visible": "y",
        "name_fa": "سالاد",
        "name_en": "Salads",
    }
    data.update(overrides)
    return data


def test_create_edit_and_delete_a_category(app, menu_data) -> None:
    client = staff_client(app, "manager")
    assert client.post("/admin/menu/categories/new", data=category_form()).status_code == 302
    category = db.session.query(Category).filter_by(slug="salads").one()
    assert {row.language.code: row.name for row in category.translations} == {
        "fa": "سالاد",
        "en": "Salads",
    }
    client.post(
        f"/admin/menu/categories/{category.id}", data=category_form(slug="fresh-salads", name_en="")
    )
    db.session.refresh(category)
    assert category.slug == "fresh-salads" and [
        row.language.code for row in category.translations
    ] == ["fa"]
    client.post(f"/admin/menu/categories/{category.id}/delete")
    assert db.session.get(Category, category.id) is None


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"slug": "pizza"}, "این شناسه برای دسته‌بندی دیگری"),
        ({"slug": "Bad Slug!"}, "فقط می‌تواند حروف کوچک"),
        ({"slug": ""}, "فقط می‌تواند حروف کوچک"),
        ({"name_fa": ""}, "نام را وارد کنید"),
    ],
)
def test_invalid_category_forms(app, menu_data, overrides, message) -> None:
    client = staff_client(app, "manager")
    response = client.post("/admin/menu/categories/new", data=category_form(**overrides))
    assert response.status_code == 200 and message in response.get_data(as_text=True)
    assert db.session.query(Category).count() == 2


def test_category_with_dishes_cannot_be_deleted(app, menu_data) -> None:
    client = staff_client(app, "manager")
    response = client.post(
        f"/admin/menu/categories/{menu_data['pizza'].id}/delete", follow_redirects=True
    )
    assert "هنوز غذا دارد" in response.get_data(as_text=True)
    assert db.session.get(Category, menu_data["pizza"].id) is not None


def test_move_category(app, menu_data) -> None:
    client = staff_client(app, "manager")
    client.post(f"/admin/menu/categories/{menu_data['drinks'].id}/move", data={"direction": "up"})
    page = client.get("/admin/menu/categories").get_data(as_text=True)
    assert page.index("نوشیدنی") < page.index("پیتزا")
    public = app.test_client().get("/fa/menu").get_data(as_text=True)
    assert public.index("نوشیدنی") < public.index("پیتزا") or "نوشابه" not in public


def test_category_pages_in_english(app, menu_data) -> None:
    client = staff_client(app, "manager")
    client.get("/admin/language/en")
    page = client.get("/admin/menu/categories").get_data(as_text=True)
    assert "Pizza" in page and "Add a category" in page
