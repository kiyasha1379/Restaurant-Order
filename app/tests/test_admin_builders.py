"""The builders section of the panel: permissions, CRUD, pictures, order and the seed."""

from io import BytesIO
from pathlib import Path

import pytest

from restaurant.extensions import db
from restaurant.models import Builder, BuilderOption, BuilderStep
from restaurant.seed.demo_builders import DEMO_BUILDERS
from restaurant.service_factory import make_demo_seed_service
from tests.helpers import add_builder, make_image_bytes, option_ids, staff_client


@pytest.fixture
def builder(app) -> Builder:
    built = add_builder()
    db.session.commit()
    return built


def builder_form(**overrides) -> dict:
    data = {
        "key": "wrap",
        "preview_kind": "sandwich",
        "sort_order": "0",
        "is_visible": "y",
        "name_fa": "رپ دلخواه",
        "name_en": "Custom wrap",
        "hint_fa": "نان و مواد را انتخاب کنید",
        "hint_en": "",
    }
    data.update(overrides)
    return {key: value for key, value in data.items() if value is not None}


def step_form(**overrides) -> dict:
    data = {
        "key": "wrap-bread",
        "sort_order": "0",
        "is_required": "y",
        "preview_role": "bread",
        "title_fa": "نان",
        "title_en": "Bread",
    }
    data.update(overrides)
    return {key: value for key, value in data.items() if value is not None}


def option_form(**overrides) -> dict:
    data = {
        "key": "pita",
        "price": "۴۰٬۰۰۰",
        "sort_order": "0",
        "is_in_stock": "y",
        "is_visible": "y",
        "color": "#C98B3E",
        "shape": "flat",
        "preview_amount": "30",
        "name_fa": "لواش",
        "name_en": "Lavash",
    }
    data.update(overrides)
    return {key: value for key, value in data.items() if value is not None}


def uploaded_files(app) -> list[Path]:
    root = Path(app.config["UPLOAD_FOLDER"])
    return sorted(root.rglob("*.webp")) if root.exists() else []


def step_of(builder: Builder, key: str) -> BuilderStep:
    return next(step for step in builder.steps if step.key == key)


# --- access ------------------------------------------------------------------------


def test_the_section_is_in_the_sidebar_for_roles_that_may_use_it(app, builder) -> None:
    page = staff_client(app, "manager").get("/admin/builders").get_data(as_text=True)
    assert "ساندویچ دلخواه" in page and "/admin/builders" in page


def test_a_role_without_the_permission_is_refused(app, builder) -> None:
    client = staff_client(app, "kitchen")
    assert client.get("/admin/builders").status_code == 403
    assert client.post("/admin/builders/new", data=builder_form()).status_code == 403
    assert db.session.query(Builder).count() == 1


def test_view_only_access_shows_pages_but_refuses_changes(app, builder) -> None:
    client = staff_client(app, "viewer")
    page = client.get("/admin/builders").get_data(as_text=True)
    assert "ساندویچ دلخواه" in page and "افزودن سازنده" not in page
    assert client.get(f"/admin/builders/{builder.id}").status_code == 200
    assert client.get("/admin/builders/new").status_code == 403
    assert client.post(f"/admin/builders/{builder.id}/delete").status_code == 403
    assert db.session.get(Builder, builder.id) is not None


# --- builders -------------------------------------------------------------------------


def test_create_a_builder_with_both_languages(app) -> None:
    client = staff_client(app, "manager")
    response = client.post("/admin/builders/new", data=builder_form())
    assert response.status_code == 302
    created = db.session.query(Builder).filter_by(key="wrap").one()
    assert {row.language.code: row.name for row in created.translations} == {
        "fa": "رپ دلخواه",
        "en": "Custom wrap",
    }
    assert client.get(response.headers["Location"]).status_code == 200


def test_the_english_name_is_optional_and_removable(app, builder) -> None:
    client = staff_client(app, "manager")
    response = client.post(
        f"/admin/builders/{builder.id}",
        data=builder_form(key="sandwich", name_fa="ساندویچ", name_en=""),
    )
    assert response.status_code == 302
    db.session.refresh(builder)
    assert [row.language.code for row in builder.translations] == ["fa"]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"name_fa": " "}, "نام فارسی لازم است"),
        ({"key": "Bad Key!"}, "کلید فقط حروف کوچک"),
        ({"key": ""}, "کلید فقط حروف کوچک"),
        ({"key": "sandwich"}, "این کلید قبلاً"),
        ({"preview_kind": "hologram"}, "یکی از گزینه‌ها"),
        ({"sort_order": "-3"}, "عدد"),
    ],
)
def test_builder_form_errors_are_shown_and_nothing_is_saved(
    app, builder, overrides, message
) -> None:
    client = staff_client(app, "manager")
    response = client.post("/admin/builders/new", data=builder_form(**overrides))
    assert response.status_code == 200 and message in response.get_data(as_text=True)
    assert db.session.query(Builder).count() == 1


def test_a_missing_builder_is_404(app) -> None:
    client = staff_client(app, "manager")
    assert client.get("/admin/builders/999").status_code == 404
    assert client.post("/admin/builders/999/delete").status_code == 404


def test_changing_the_picture_kind_resets_roles_that_no_longer_fit(app, builder) -> None:
    client = staff_client(app, "manager")
    client.post(
        f"/admin/builders/{builder.id}", data=builder_form(key="sandwich", preview_kind="drink")
    )
    db.session.refresh(builder)
    assert builder.preview_kind.value == "drink"
    assert {step.preview_role for step in builder.steps} == {""}


def test_move_builders_even_when_all_orders_are_equal(app, builder) -> None:
    second = add_builder(key="second")
    db.session.commit()
    client = staff_client(app, "manager")
    client.post(f"/admin/builders/{second.id}/move", data={"direction": "up"})
    page = client.get("/admin/builders").get_data(as_text=True)
    assert page.index('dir="ltr">second<') < page.index('dir="ltr">sandwich<')
    assert (
        client.post(f"/admin/builders/{second.id}/move", data={"direction": "x"}).status_code == 400
    )


def test_delete_a_builder_removes_steps_options_and_pictures(app, builder) -> None:
    client = staff_client(app, "manager")
    option = step_of(builder, "layers").options[0]
    client.post(
        f"/admin/builders/options/{option.id}",
        data={**option_form(key=option.key), "photo": (BytesIO(make_image_bytes()), "p.png")},
        content_type="multipart/form-data",
    )
    assert len(uploaded_files(app)) == 1
    assert client.post(f"/admin/builders/{builder.id}/delete").status_code == 302
    assert db.session.query(Builder).count() == 0
    assert db.session.query(BuilderStep).count() == 0
    assert db.session.query(BuilderOption).count() == 0
    assert uploaded_files(app) == []


# --- steps -----------------------------------------------------------------------------


def test_create_edit_and_delete_a_step(app, builder) -> None:
    client = staff_client(app, "manager")
    response = client.post(f"/admin/builders/{builder.id}/steps/new", data=step_form(key="extras"))
    assert response.status_code == 302
    step = db.session.query(BuilderStep).filter_by(key="extras").one()
    assert step.builder_id == builder.id and step.preview_role == "bread"
    assert client.get(response.headers["Location"]).status_code == 200
    client.post(
        f"/admin/builders/steps/{step.id}", data=step_form(key="extras", title_fa="افزودنی")
    )
    db.session.refresh(step)
    assert [row.title for row in step.translations if row.language.code == "fa"] == ["افزودنی"]
    assert client.post(f"/admin/builders/steps/{step.id}/delete").status_code == 302
    assert db.session.query(BuilderStep).filter_by(key="extras").count() == 0


def test_layered_steps_are_always_multiple(app, builder) -> None:
    client = staff_client(app, "manager")
    client.post(
        f"/admin/builders/{builder.id}/steps/new",
        data=step_form(key="stack", is_layered="y", is_multiple=None, preview_role="layer"),
    )
    step = db.session.query(BuilderStep).filter_by(key="stack").one()
    assert step.is_layered and step.is_multiple


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"key": "bread"}, "این کلید قبلاً"),
        ({"key": "No Good"}, "کلید فقط حروف کوچک"),
        ({"preview_role": "crust"}, "یکی از گزینه‌ها"),  # a pizza role on a sandwich builder
        ({"title_fa": ""}, "نام فارسی لازم است"),
    ],
)
def test_step_form_errors_are_shown(app, builder, overrides, message) -> None:
    client = staff_client(app, "manager")
    response = client.post(f"/admin/builders/{builder.id}/steps/new", data=step_form(**overrides))
    assert response.status_code == 200 and message in response.get_data(as_text=True)
    assert len(db.session.get(Builder, builder.id).steps) == 3


def test_the_same_step_key_may_be_used_by_another_builder(app, builder) -> None:
    other = add_builder(key="other")
    db.session.commit()
    client = staff_client(app, "manager")
    response = client.post(f"/admin/builders/{other.id}/steps/new", data=step_form(key="extras"))
    assert response.status_code == 302
    client.post(f"/admin/builders/{builder.id}/steps/new", data=step_form(key="extras"))
    assert db.session.query(BuilderStep).filter_by(key="extras").count() == 2


def test_move_steps(app, builder) -> None:
    client = staff_client(app, "manager")
    sauce = step_of(builder, "sauce")
    client.post(f"/admin/builders/steps/{sauce.id}/move", data={"direction": "up"})
    db.session.expire_all()
    assert [step.key for step in db.session.get(Builder, builder.id).steps] == [
        "bread",
        "sauce",
        "layers",
    ]


# --- options ---------------------------------------------------------------------------


def test_create_an_option_with_a_picture(app, builder) -> None:
    client = staff_client(app, "manager")
    step = step_of(builder, "bread")
    response = client.post(
        f"/admin/builders/steps/{step.id}/options/new",
        data={**option_form(), "photo": (BytesIO(make_image_bytes()), "photo.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    option = db.session.query(BuilderOption).filter_by(key="pita").one()
    assert option.step_id == step.id and option.price == 40_000
    assert (option.color, option.shape, option.preview_amount) == ("#C98B3E", "flat", 30)
    assert option.layer_image.startswith("uploads/builders/")
    assert len(uploaded_files(app)) == 1
    assert client.get(f"/admin/builders/options/{option.id}").status_code == 200


def test_replacing_and_removing_the_picture_deletes_the_old_file(app, builder) -> None:
    client = staff_client(app, "manager")
    option = step_of(builder, "bread").options[0]
    url = f"/admin/builders/options/{option.id}"
    for _ in range(2):
        client.post(
            url,
            data={**option_form(key=option.key), "photo": (BytesIO(make_image_bytes()), "p.png")},
            content_type="multipart/form-data",
        )
    assert len(uploaded_files(app)) == 1
    client.post(url, data=option_form(key=option.key, remove_photo="y"))
    db.session.refresh(option)
    assert option.layer_image is None and uploaded_files(app) == []


def test_a_bad_picture_is_refused_and_nothing_is_saved(app, builder) -> None:
    client = staff_client(app, "manager")
    step = step_of(builder, "bread")
    response = client.post(
        f"/admin/builders/steps/{step.id}/options/new",
        data={**option_form(), "photo": (BytesIO(b"not a picture"), "x.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert db.session.query(BuilderOption).filter_by(key="pita").count() == 0


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"key": "toast"}, "این کلید قبلاً"),
        ({"price": "abc"}, "عدد صحیح"),
        ({"price": "999999999999"}, "قیمت"),
        ({"color": "red"}, "#rrggbb"),
        ({"shape": "Round Thing"}, "#rrggbb"),
        ({"preview_amount": "500"}, "عدد"),
        ({"name_fa": ""}, "نام فارسی لازم است"),
    ],
)
def test_option_form_errors_are_shown(app, builder, overrides, message) -> None:
    client = staff_client(app, "manager")
    step = step_of(builder, "bread")
    response = client.post(
        f"/admin/builders/steps/{step.id}/options/new", data=option_form(**overrides)
    )
    assert response.status_code == 200 and message in response.get_data(as_text=True)
    assert db.session.query(BuilderOption).filter_by(key="pita").count() == 0


def test_stock_visibility_and_move_of_options(app, builder) -> None:
    client = staff_client(app, "manager")
    step = step_of(builder, "layers")
    first, second = step.options[0], step.options[1]
    client.post(f"/admin/builders/options/{first.id}/stock", data={"value": "0"})
    client.post(f"/admin/builders/options/{first.id}/visible", data={"value": "0"})
    db.session.refresh(first)
    assert not first.is_in_stock and not first.is_visible
    client.post(f"/admin/builders/options/{second.id}/move", data={"direction": "up"})
    db.session.expire_all()
    assert [o.key for o in db.session.get(BuilderStep, step.id).options][:2] == ["tomato", "cheese"]
    assert (
        client.post(
            f"/admin/builders/options/{second.id}/move", data={"direction": "?"}
        ).status_code
        == 400
    )


def test_a_sold_out_option_is_refused_by_the_resolver_after_the_toggle(app, builder) -> None:
    from restaurant.services import InvalidSelectionError

    client = staff_client(app, "manager")
    ids = option_ids(builder, "baguette", "steak", "mayo")
    client.post(f"/admin/builders/options/{ids[1]}/stock", data={"value": "0"})
    from restaurant.service_factory import make_build_resolver

    with pytest.raises(InvalidSelectionError):
        make_build_resolver().resolve(builder.id, ids, "fa")


def test_delete_an_option(app, builder) -> None:
    client = staff_client(app, "manager")
    option = step_of(builder, "layers").options[0]
    assert client.post(f"/admin/builders/options/{option.id}/delete").status_code == 302
    assert db.session.get(BuilderOption, option.id) is None


def test_the_option_page_for_a_missing_row_is_404(app) -> None:
    client = staff_client(app, "manager")
    assert client.get("/admin/builders/options/999").status_code == 404
    assert client.get("/admin/builders/steps/999").status_code == 404
    assert client.get("/admin/builders/999/steps/new").status_code == 404


def test_next_must_be_a_panel_address(app, builder) -> None:
    client = staff_client(app, "manager")
    option = step_of(builder, "layers").options[0]
    response = client.post(
        f"/admin/builders/options/{option.id}/stock",
        data={"value": "0", "next": "https://evil.example/"},
    )
    assert "evil.example" not in response.headers["Location"]


# --- the demo seed ---------------------------------------------------------------------------


def test_seeding_adds_the_demo_builders_once(app) -> None:
    service = make_demo_seed_service()
    assert service.seed().builders == len(DEMO_BUILDERS)
    db.session.commit()
    assert service.seed().builders == 0
    assert db.session.query(Builder).count() == len(DEMO_BUILDERS)


def test_every_demo_option_has_both_names_and_a_valid_role(app) -> None:
    from restaurant.constants import PREVIEW_ROLES_BY_KIND

    make_demo_seed_service().seed()
    db.session.commit()
    for builder in db.session.query(Builder):
        allowed = {role.value for role in PREVIEW_ROLES_BY_KIND[builder.preview_kind]}
        for step in builder.steps:
            assert step.preview_role in allowed
            assert {row.language.code for row in step.translations} == {"fa", "en"}
            for option in step.options:
                assert {row.language.code for row in option.translations} == {"fa", "en"}
