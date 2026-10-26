"""The admin Site appearance section: brand, logo, accent colour, backgrounds, home sections."""

from io import BytesIO

import pytest

from restaurant.extensions import db
from restaurant.models import Background, SiteSection
from restaurant.service_factory import make_site_appearance_service, make_site_settings_service
from restaurant.services import SiteAppearanceError
from tests.helpers import add_category, add_dish, make_image_bytes, staff_client

MP4 = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2" + b"\x00" * 200


def upload(data: bytes, name: str) -> tuple[BytesIO, str]:
    return BytesIO(data), name


def uploaded(app) -> list[str]:
    root = app.config["UPLOAD_FOLDER"]
    return sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())


def brand_form(**changes) -> dict:
    form = {"brand_name": "رستوران آزمایشی", "accent_color": "#2f7d6b"}
    form.update(changes)
    return form


def home_order(client) -> list[str]:
    """Return the section ids of the public home page in page order."""
    import re

    page = client.get("/fa/").get_data(as_text=True)
    return re.findall(r'<section class="screen[^"]*" id="([a-z]+)"', page)


# Permissions ------------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/admin/site", "/admin/site/backgrounds", "/admin/site/home"])
def test_manager_opens_every_tab_and_cashier_is_refused(app, path) -> None:
    assert staff_client(app, "manager").get(path).status_code == 200
    assert staff_client(app, "cashier").get(path).status_code == 403


def test_viewer_cannot_change_anything(app) -> None:
    viewer = staff_client(app, "viewer")
    assert viewer.get("/admin/site").status_code == 200
    assert viewer.post("/admin/site", data=brand_form()).status_code == 403
    assert (
        viewer.post("/admin/site/backgrounds/home-hero", data={"dim_percent": "10"}).status_code
        == 403
    )
    assert viewer.post("/admin/site/home/sections", data={"order": ["how"]}).status_code == 403
    assert viewer.post("/admin/site/home/texts", data={}).status_code == 403


# Brand, colour and logo -------------------------------------------------------------------


def test_brand_name_and_accent_reach_the_public_pages(app) -> None:
    client = staff_client(app, "manager")
    assert client.post("/admin/site", data=brand_form()).status_code == 302
    page = app.test_client().get("/fa/").get_data(as_text=True)
    assert "رستوران آزمایشی" in page and "--color-accent:#2f7d6b" in page


def test_default_colour_checkbox_restores_the_built_in_colour(app) -> None:
    client = staff_client(app, "manager")
    client.post("/admin/site", data=brand_form())
    client.post("/admin/site", data=brand_form(use_default_color="y"))
    assert make_site_settings_service().get_site_look().accent_color is None
    assert "--color-accent:#2f7d6b" not in app.test_client().get("/fa/").get_data(as_text=True)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"brand_name": "  "}, "بین ۱ تا ۶۰"),
        ({"brand_name": "x" * 61}, "بین ۱ تا ۶۰"),
        ({"accent_color": "red"}, "#RRGGBB"),
        ({"accent_color": "#12345"}, "#RRGGBB"),
        ({"accent_color": "url(javascript:alert(1))"}, "#RRGGBB"),
    ],
)
def test_bad_brand_values_are_refused(app, changes, message) -> None:
    response = staff_client(app, "manager").post("/admin/site", data=brand_form(**changes))
    assert response.status_code == 422 and message in response.get_data(as_text=True)
    assert make_site_settings_service().get_site_look().accent_color is None


def test_logo_is_stored_shown_replaced_and_removed(app) -> None:
    client = staff_client(app, "manager")
    send = lambda **extra: client.post(  # noqa: E731
        "/admin/site", data={**brand_form(), **extra}, content_type="multipart/form-data"
    )
    send(logo=upload(make_image_bytes(), "logo.png"))
    first = uploaded(app)
    assert len(first) == 1 and first[0].startswith("site/")
    assert "brand-logo" in app.test_client().get("/en/").get_data(as_text=True)
    send(logo=upload(make_image_bytes(), "again.png"))
    second = uploaded(app)
    assert len(second) == 1 and second != first
    send(remove_logo="y")
    assert uploaded(app) == []
    assert "brand-logo" not in app.test_client().get("/en/").get_data(as_text=True)


def test_a_fake_logo_is_refused_and_nothing_is_stored(app) -> None:
    response = staff_client(app, "manager").post(
        "/admin/site",
        data={**brand_form(), "logo": upload(b"<svg onload=alert(1)>", "logo.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 422 and uploaded(app) == []


# Backgrounds ------------------------------------------------------------------------------


def background_form(**changes) -> dict:
    form = {"dim_percent": "55", "is_enabled": "y", "mobile_mode": "video"}
    form.update(changes)
    return form


def test_every_known_background_is_listed_even_before_it_is_stored(app) -> None:
    page = staff_client(app, "manager").get("/admin/site/backgrounds").get_data(as_text=True)
    for key in ("home-hero", "home-footer", "menu-page", "builder-page", "reserve-page"):
        assert f'id="bg-{key}"' in page


def test_saving_a_background_creates_it_and_changes_the_public_page(app) -> None:
    client = staff_client(app, "manager")
    assert db.session.query(Background).count() == 0
    response = client.post("/admin/site/backgrounds/home-hero", data=background_form())
    assert response.status_code == 302
    stored = db.session.query(Background).one()
    assert (stored.key, stored.dim, stored.is_enabled) == ("home-hero", 0.55, True)
    assert 'style="--bg-dim: 0.55"' in app.test_client().get("/fa/").get_data(as_text=True)


def test_a_switched_off_background_is_not_drawn(app) -> None:
    client = staff_client(app, "manager")
    client.post("/admin/site/backgrounds/home-hero", data=background_form(is_enabled=None))
    assert make_site_appearance_service().list_backgrounds()[0].is_enabled is False


@pytest.mark.parametrize("value", ["-1", "101", "abc", ""])
def test_dim_must_be_between_0_and_100(app, value) -> None:
    response = staff_client(app, "manager").post(
        "/admin/site/backgrounds/home-hero", data=background_form(dim_percent=value)
    )
    assert response.status_code == 422
    assert db.session.query(Background).count() == 0


def test_unknown_background_keys_are_ignored(app) -> None:
    client = staff_client(app, "manager")
    response = client.post("/admin/site/backgrounds/../../etc", data=background_form())
    assert response.status_code in {302, 404}
    assert client.post("/admin/site/backgrounds/evil", data=background_form()).status_code == 302
    assert db.session.query(Background).count() == 0


def test_poster_and_video_upload_replace_and_remove_with_cleanup(app) -> None:
    client = staff_client(app, "manager")
    url = "/admin/site/backgrounds/menu-page"
    post = lambda **extra: client.post(  # noqa: E731
        url, data={**background_form(), **extra}, content_type="multipart/form-data"
    )
    post(poster=upload(make_image_bytes(size=(800, 500)), "p.png"), video=upload(MP4, "v.mp4"))
    files = uploaded(app)
    assert len(files) == 2 and any(name.endswith(".mp4") for name in files)
    row = db.session.query(Background).one()
    assert row.poster_path.startswith("uploads/backgrounds/")
    assert row.video_path.startswith("uploads/backgrounds/")

    post(video=upload(MP4, "v2.mp4"))
    after_replace = uploaded(app)
    assert len(after_replace) == 2 and after_replace != files

    post(remove_video="y", remove_poster="y")
    assert uploaded(app) == []
    db.session.refresh(row)
    assert row.video_path is None and row.poster_path is None


def test_removing_a_seeded_file_never_deletes_files_outside_uploads(app) -> None:
    db.session.add(
        Background(key="home-hero", video_path="media/backgrounds/home-hero.mp4", poster_path=None)
    )
    db.session.commit()
    staff_client(app, "manager").post(
        "/admin/site/backgrounds/home-hero", data=background_form(remove_video="y")
    )
    assert db.session.query(Background).one().video_path is None


@pytest.mark.parametrize(
    ("field", "data", "message"),
    [
        ("video", b"not a video at all", "ویدیوی MP4"),
        ("video", b"\x00\x00\x00\x18ftyp" + b"\x00" * (13 * 1024 * 1024), "۱۲ مگابایت"),
        ("poster", b"<svg onload=alert(1)>", ""),
    ],
)
def test_bad_media_is_refused_and_leaves_no_file(app, field, data, message) -> None:
    response = staff_client(app, "manager").post(
        "/admin/site/backgrounds/home-hero",
        data={**background_form(), field: upload(data, "x.bin")},
        content_type="multipart/form-data",
    )
    assert response.status_code in {413, 422}
    if response.status_code == 422:
        assert message in response.get_data(as_text=True)
    assert uploaded(app) == []
    assert db.session.query(Background).count() == 0


def test_a_failed_poster_does_not_keep_a_good_video(app) -> None:
    response = staff_client(app, "manager").post(
        "/admin/site/backgrounds/home-hero",
        data={
            **background_form(),
            "video": upload(MP4, "v.mp4"),
            "poster": upload(b"junk", "p.png"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 422 and uploaded(app) == []


# Home sections ----------------------------------------------------------------------------


@pytest.fixture
def one_dish(app) -> None:
    """A chef's pick, so the dishes section appears on the home page."""
    category = add_category("a", {"fa": "الف", "en": "A"})
    add_dish(category, {"fa": "کباب", "en": "Kebab"}, base_price=280_000, is_chefs_pick=True)
    db.session.commit()


def post_sections(client, order, visible=None, move=None):
    data = {"order": order, "visible": order if visible is None else visible}
    if move:
        data["move"] = move
    return client.post("/admin/site/home/sections", data=data)


def test_default_order_is_modes_dishes_how_reserve(app, one_dish) -> None:
    assert home_order(app.test_client()) == ["top", "modes", "dishes", "how", "reserve", "contact"]


def test_moving_a_section_changes_the_home_page(app, one_dish) -> None:
    client = staff_client(app, "manager")
    post_sections(client, ["modes", "dishes", "how", "reserve"], move="reserve:up")
    assert home_order(app.test_client()) == ["top", "modes", "dishes", "reserve", "how", "contact"]
    post_sections(client, ["modes", "dishes", "reserve", "how"], move="modes:down")
    assert home_order(app.test_client()) == ["top", "dishes", "modes", "reserve", "how", "contact"]


def test_moving_past_the_ends_changes_nothing(app, one_dish) -> None:
    client = staff_client(app, "manager")
    post_sections(client, ["modes", "dishes", "how", "reserve"], move="modes:up")
    post_sections(client, ["modes", "dishes", "how", "reserve"], move="reserve:down")
    assert home_order(app.test_client()) == ["top", "modes", "dishes", "how", "reserve", "contact"]


def test_hidden_sections_leave_the_page_and_the_dots(app, one_dish) -> None:
    client = staff_client(app, "manager")
    post_sections(client, ["modes", "dishes", "how", "reserve"], visible=["modes", "how"])
    visitor = app.test_client()
    assert home_order(visitor) == ["top", "modes", "how", "contact"]
    page = visitor.get("/fa/").get_data(as_text=True)
    assert 'data-section-link="dishes"' not in page and 'data-section-link="how"' in page


def test_the_hero_and_the_footer_are_always_there(app) -> None:
    post_sections(staff_client(app, "manager"), ["modes", "dishes", "how", "reserve"], visible=[])
    assert home_order(app.test_client()) == ["top", "contact"]


@pytest.mark.parametrize(
    "order",
    [["modes", "how"], ["modes", "modes", "how", "reserve"], ["modes", "dishes", "how", "evil"]],
)
def test_a_broken_order_is_refused_and_keeps_the_old_one(app, one_dish, order) -> None:
    post_sections(staff_client(app, "manager"), order)
    assert db.session.query(SiteSection).count() == 0
    assert home_order(app.test_client()) == ["top", "modes", "dishes", "how", "reserve", "contact"]


def test_service_refuses_unknown_visible_keys(app) -> None:
    with pytest.raises(SiteAppearanceError):
        make_site_appearance_service().save_home_sections(
            ["modes", "dishes", "how", "reserve"], {"nope"}
        )


def test_a_section_added_later_shows_after_the_stored_ones(app, one_dish) -> None:
    db.session.add_all(
        [
            SiteSection(key="how", position=0, is_visible=True),
            SiteSection(key="modes", position=1, is_visible=True),
        ]
    )
    db.session.commit()
    assert make_site_appearance_service().visible_home_sections() == [
        "how",
        "modes",
        "dishes",
        "reserve",
    ]


# Home texts -------------------------------------------------------------------------------


def test_home_texts_are_edited_and_shown(app) -> None:
    client = staff_client(app, "manager")
    page = client.get("/admin/site/home").get_data(as_text=True)
    assert 'name="home.headline.fa"' in page and 'name="home.headline.en"' in page
    response = client.post(
        "/admin/site/home/texts",
        data={"home.headline.fa": "عنوان تازه", "home.headline.en": "A fresh headline"},
    )
    assert response.status_code == 302
    assert "عنوان تازه" in app.test_client().get("/fa/").get_data(as_text=True)
    assert "A fresh headline" in app.test_client().get("/en/").get_data(as_text=True)


def test_only_the_listed_home_texts_can_be_changed_here(app) -> None:
    staff_client(app, "manager").post(
        "/admin/site/home/texts",
        data={"footer.phone_value.fa": "hacked", "admin.save.fa": "hacked", "home.lead.fa": "ok"},
    )
    assert "hacked" not in app.test_client().get("/fa/").get_data(as_text=True)
    assert "ok" in app.test_client().get("/fa/").get_data(as_text=True)
