"""The builders: checking and pricing a build, the cart, the order, the API and the pages."""

import pytest

from restaurant import create_app
from restaurant.constants import FulfillmentType, PaymentMethod
from restaurant.extensions import db
from restaurant.models import Builder, BuilderOption, Order
from restaurant.service_factory import (
    make_build_resolver,
    make_cart_service,
    make_order_service,
    make_pricing_service,
)
from restaurant.services import (
    CartLine,
    CartService,
    CustomBuild,
    InvalidSelectionError,
    PlaceOrderRequest,
    SelectionProblem,
)
from tests.helpers import add_builder, option_ids


@pytest.fixture
def builder(app) -> Builder:
    built = add_builder()
    db.session.commit()
    return built


def resolve(builder: Builder, *keys: str, language: str = "fa"):
    return make_build_resolver().resolve(builder.id, option_ids(builder, *keys), language)


def problem_of(builder: Builder, ids: list[int]) -> SelectionProblem:
    with pytest.raises(InvalidSelectionError) as caught:
        make_build_resolver().resolve(builder.id, ids, "fa")
    return caught.value.problem


# --- the resolver ----------------------------------------------------------


def test_a_valid_build_is_priced_from_the_options(builder) -> None:
    build = resolve(builder, "baguette", "cheese", "steak", "mayo")
    assert build.unit_price == 60_000 + 20_000 + 45_000
    assert build.name == "ساندویچ دلخواه" and build.name_en == "Custom sandwich"


def test_names_follow_the_language_and_keep_both_for_the_snapshot(builder) -> None:
    english = resolve(builder, "toast", "mayo", language="en")
    assert [option.name for option in english.options] == ["Toast", "Mayo"]
    assert english.options[0].group == "Bread" and english.options[0].group_fa == "نان"
    assert english.options[0].name_fa == "نان تست"


def test_plain_options_follow_step_order_and_layers_keep_the_customers_order(builder) -> None:
    ids = option_ids(builder, "steak", "mayo", "cheese", "baguette", "tomato")
    build = make_build_resolver().resolve(builder.id, ids, "fa")
    order = [option.name_en for option in build.options]
    assert order == ["Baguette", "Mayo", "Steak", "Cheese", "Tomato"]
    assert [option.order_index for option in build.options] == [0, 1, 2, 3, 4]


def test_changing_the_layer_order_changes_the_order_but_not_the_price(builder) -> None:
    first = resolve(builder, "baguette", "cheese", "tomato", "mayo")
    second = resolve(builder, "baguette", "tomato", "cheese", "mayo")
    assert first.unit_price == second.unit_price
    assert first.option_ids != second.option_ids


@pytest.mark.parametrize(
    ("keys", "problem"),
    [
        (("baguette", "toast", "mayo"), SelectionProblem.TOO_MANY),
        (("cheese", "mayo"), SelectionProblem.MISSING),
        (("baguette", "cheese"), SelectionProblem.MISSING),
        ((), SelectionProblem.MISSING),
    ],
)
def test_the_step_rules_are_enforced(builder, keys, problem) -> None:
    assert problem_of(builder, option_ids(builder, *keys)) is problem


def test_unknown_duplicate_and_foreign_options_are_refused(app, builder) -> None:
    other = add_builder(key="other")
    db.session.commit()
    good = option_ids(builder, "baguette", "mayo")
    assert problem_of(builder, good + [999_999]) is SelectionProblem.UNKNOWN
    assert problem_of(builder, good + [good[0]]) is SelectionProblem.UNKNOWN
    assert problem_of(builder, good + option_ids(other, "cheese")) is SelectionProblem.UNKNOWN
    assert problem_of(builder, list(range(1, 60))) is SelectionProblem.UNKNOWN


def test_sold_out_and_hidden_options_are_unavailable(builder) -> None:
    ids = option_ids(builder, "baguette", "steak", "mayo")
    steak = db.session.get(BuilderOption, ids[1])
    steak.is_in_stock = False
    db.session.commit()
    assert problem_of(builder, ids) is SelectionProblem.UNAVAILABLE
    steak.is_in_stock, steak.is_visible = True, False
    db.session.commit()
    assert problem_of(builder, ids) is SelectionProblem.UNAVAILABLE


def test_a_required_step_with_nothing_left_to_pick_does_not_block(builder) -> None:
    for option in next(step for step in builder.steps if step.key == "sauce").options:
        option.is_in_stock = False
    db.session.commit()
    assert resolve(builder, "baguette").unit_price == 60_000


def test_a_hidden_builder_cannot_be_built(builder) -> None:
    builder.is_visible = False
    db.session.commit()
    assert problem_of(builder, option_ids(builder, "baguette", "mayo")) is SelectionProblem.UNKNOWN


def test_the_price_follows_later_price_changes(builder) -> None:
    ids = option_ids(builder, "baguette", "mayo")
    db.session.get(BuilderOption, ids[0]).price = 99_000
    db.session.commit()
    assert make_build_resolver().resolve(builder.id, ids, "fa").unit_price == 99_000


# --- the cart ------------------------------------------------------------------


class MemoryStorage:
    def __init__(self) -> None:
        self.raw: list[dict] = []

    def load(self) -> list[dict]:
        return self.raw

    def save(self, raw_lines: list[dict]) -> None:
        self.raw = raw_lines


def test_the_same_build_merges_and_another_order_is_another_line() -> None:
    cart = CartService(MemoryStorage())
    cart.add_custom(CustomBuild(1, (4, 5, 6)), 1)
    cart.add_custom(CustomBuild(1, (4, 5, 6)), 2)
    cart.add_custom(CustomBuild(1, (4, 6, 5)), 1)
    lines = cart.lines()
    assert [line.quantity for line in lines] == [3, 1]
    assert lines[0].line_id.startswith("build-") and lines[0].dish_id is None


def test_custom_lines_survive_storage_and_damaged_ones_are_dropped() -> None:
    storage = MemoryStorage()
    cart = CartService(storage)
    cart.add_custom(CustomBuild(2, (7, 8)), 2)
    storage.raw.append({"builder_id": 0, "option_ids": [1], "quantity": 1})
    storage.raw.append({"builder_id": 1, "option_ids": [], "quantity": 1})
    storage.raw.append({"builder_id": 1, "option_ids": ["x"], "quantity": 1})
    storage.raw.append({"builder_id": 1, "option_ids": [1], "quantity": 99})
    assert [(line.custom.builder_id, line.custom.option_ids) for line in cart.lines()] == [
        (2, (7, 8))
    ]


def test_the_cart_is_capped_at_twenty_five_lines() -> None:
    from restaurant.services import CartError

    cart = CartService(MemoryStorage())
    for number in range(1, 26):
        cart.add_custom(CustomBuild(1, (number,)), 1)
    with pytest.raises(CartError):
        cart.add_custom(CustomBuild(1, (99,)), 1)


def test_quantity_of_a_custom_line_can_change_and_be_removed() -> None:
    cart = CartService(MemoryStorage())
    cart.add_custom(CustomBuild(1, (3,)), 1)
    line_id = cart.lines()[0].line_id
    cart.set_quantity(line_id, 5)
    assert cart.lines()[0].quantity == 5
    cart.set_quantity(line_id, 0)
    assert cart.lines() == []


# --- pricing and orders ---------------------------------------------------------


def build_line(builder: Builder, *keys: str, quantity: int = 1) -> CartLine:
    custom = CustomBuild(builder.id, tuple(option_ids(builder, *keys)))
    return CartLine(CartService.custom_line_id(custom), None, quantity, custom)


def order_request(**fields) -> PlaceOrderRequest:
    values = {
        "customer_name": "Ali",
        "customer_phone": "09123456789",
        "fulfillment": FulfillmentType.TAKEAWAY,
        "delivery_address": "",
        "note": "",
        "payment_method": PaymentMethod.CASH_ON_SITE,
        "language_code": "fa",
    }
    return PlaceOrderRequest(**{**values, **fields})


def test_a_custom_line_is_priced_by_the_server(builder) -> None:
    line = build_line(builder, "baguette", "cheese", "mayo", quantity=2)
    priced = make_pricing_service().price([line], FulfillmentType.TAKEAWAY, "fa")
    assert priced.lines[0].unit_price == 80_000 and priced.total == 160_000
    assert "باگت" in priced.lines[0].summary and "پنیر" in priced.lines[0].summary


def test_an_invalid_custom_line_is_reported_unavailable(builder) -> None:
    line = build_line(builder, "baguette", "toast", "mayo")  # two breads
    priced = make_pricing_service().price([line], FulfillmentType.TAKEAWAY, "fa")
    assert priced.lines == [] and priced.unavailable_line_ids == {line.line_id}


def test_the_order_stores_options_with_order_and_group_names(builder) -> None:
    line = build_line(builder, "baguette", "steak", "cheese", "mayo")
    order = make_order_service().place_order(order_request(), [line])
    db.session.commit()
    item = db.session.get(Order, order.id).items[0]
    assert item.dish_id is None and item.unit_price == 125_000 and item.name_fa == "ساندویچ دلخواه"
    assert [option.name_en for option in item.options] == ["Baguette", "Mayo", "Steak", "Cheese"]
    assert [option.order_index for option in item.options] == [0, 1, 2, 3]
    assert item.options[0].group_fa == "نان" and item.options[0].group_en == "Bread"
    assert sum(option.price for option in item.options) == item.unit_price


def test_an_order_survives_later_option_edits_and_deletion(builder) -> None:
    line = build_line(builder, "baguette", "cheese", "mayo")
    order = make_order_service().place_order(order_request(), [line])
    db.session.commit()
    cheese = db.session.get(BuilderOption, line.custom.option_ids[1])
    cheese.price = 1
    db.session.commit()
    db.session.delete(db.session.get(Builder, builder.id))
    db.session.commit()
    item = db.session.get(Order, order.id).items[0]
    assert sorted(option.price for option in item.options) == [0, 20_000, 60_000]
    assert item.line_total == 80_000


def test_a_refused_build_cannot_be_ordered(builder) -> None:
    from restaurant.services import UnavailableDishError

    line = build_line(builder, "baguette")  # the sauce step is missing
    with pytest.raises(UnavailableDishError):
        make_order_service().place_order(order_request(), [line])


# --- the JSON API -----------------------------------------------------------------


def quote(client, key, ids, quantity=1, **query):
    return client.post(
        f"/api/builders/{key}/quote",
        json={"option_ids": ids, "quantity": quantity},
        query_string=query,
    )


def add_custom(client, key, ids, quantity=1, **query):
    return client.post(
        "/api/cart/add-custom",
        json={"builder": key, "option_ids": ids, "quantity": quantity},
        query_string=query,
    )


def test_quote_returns_the_server_price(client, builder) -> None:
    ids = option_ids(builder, "toast", "tomato", "ketchup")
    data = quote(client, "sandwich", ids, 3).get_json()
    assert (data["unit_price"], data["quantity"], data["total"]) == (60_000, 3, 180_000)


def test_quote_errors_are_in_the_page_language(client, builder) -> None:
    bad = option_ids(builder, "baguette", "toast", "mayo")
    persian = quote(client, "sandwich", bad)
    english = quote(client, "sandwich", bad, lang="en")
    assert persian.status_code == english.status_code == 400
    assert persian.get_json()["error"] != english.get_json()["error"]


def test_quote_for_an_unknown_builder_is_404(client, builder) -> None:
    assert quote(client, "nope", [1]).status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"option_ids": "1,2"},
        {"option_ids": [1, "2"]},
        {"option_ids": [True]},
        {"option_ids": [1], "quantity": 0},
        {"option_ids": [1], "quantity": 99},
        {"option_ids": [1], "quantity": "2"},
    ],
)
def test_malformed_quote_bodies_are_rejected(client, builder, body) -> None:
    assert client.post("/api/builders/sandwich/quote", json=body).status_code == 400


def test_the_browser_cannot_set_a_price_for_a_build(client, builder) -> None:
    ids = option_ids(builder, "baguette", "mayo")
    response = client.post(
        "/api/cart/add-custom",
        json={"builder": "sandwich", "option_ids": ids, "quantity": 1, "price": 1},
    )
    assert response.get_json()["lines"][0]["unit_price"] == 60_000


def test_add_custom_fills_the_cart_and_merges_equal_builds(client, builder) -> None:
    ids = option_ids(builder, "baguette", "cheese", "mayo")
    add_custom(client, "sandwich", ids)
    data = add_custom(client, "sandwich", ids, 2).get_json()
    assert data["count"] == 3 and len(data["lines"]) == 1
    assert data["lines"][0]["line_total"] == 240_000
    assert "پنیر" in data["lines"][0]["summary"]
    english = client.get("/api/cart?lang=en").get_json()
    assert "Cheese" in english["lines"][0]["summary"]


def test_add_custom_refuses_unavailable_and_invalid_builds(client, builder) -> None:
    ids = option_ids(builder, "baguette", "steak", "mayo")
    db.session.get(BuilderOption, ids[1]).is_in_stock = False
    db.session.commit()
    assert add_custom(client, "sandwich", ids).status_code == 409
    assert add_custom(client, "sandwich", ids[:1]).status_code == 400
    assert add_custom(client, "nope", ids).status_code == 404
    assert client.post("/api/cart/add-custom", json={"option_ids": ids}).status_code == 400
    assert client.get("/api/cart").get_json()["count"] == 0


def test_custom_lines_can_be_updated_through_the_cart_api(client, builder) -> None:
    ids = option_ids(builder, "baguette", "mayo")
    line_id = add_custom(client, "sandwich", ids).get_json()["lines"][0]["line_id"]
    assert (
        client.post("/api/cart/update", json={"line_id": line_id, "quantity": 4}).get_json()[
            "count"
        ]
        == 4
    )


def test_a_build_that_becomes_unavailable_is_dropped_from_the_cart(client, builder) -> None:
    ids = option_ids(builder, "baguette", "mayo")
    add_custom(client, "sandwich", ids)
    db.session.get(BuilderOption, ids[0]).is_in_stock = False
    db.session.commit()
    data = client.get("/api/cart").get_json()
    assert data["count"] == 0 and data["removed_unavailable"] is True


def test_build_writes_need_the_csrf_token_when_protection_is_on(builder) -> None:
    app = create_app("test", {"WTF_CSRF_ENABLED": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    with app.app_context():
        db.create_all()
        from tests.conftest import add_two_languages

        add_two_languages()
        response = app.test_client().post(
            "/api/builders/sandwich/quote", json={"option_ids": [1], "quantity": 1}
        )
        assert response.status_code == 400
        db.session.remove()
        db.drop_all()


# --- the pages -------------------------------------------------------------------------


def test_the_builder_page_renders_in_both_languages(client, builder) -> None:
    persian = client.get("/fa/build/sandwich").get_data(as_text=True)
    english = client.get("/en/build/sandwich").get_data(as_text=True)
    assert "ساندویچ دلخواه" in persian and "باگت" in persian and 'dir="rtl"' in persian
    assert "Custom sandwich" in english and "Baguette" in english and 'dir="ltr"' in english
    assert 'id="builder-data"' in persian


def test_build_opens_the_first_builder_and_unknown_keys_are_404(client, builder) -> None:
    response = client.get("/fa/build")
    assert response.status_code == 302 and response.headers["Location"].endswith(
        "/fa/build/sandwich"
    )
    assert client.get("/fa/build/nope").status_code == 404


def test_build_without_builders_goes_to_the_menu(client) -> None:
    response = client.get("/fa/build")
    assert response.status_code == 302 and response.headers["Location"].endswith("/fa/menu")


def test_hidden_builders_and_options_are_not_shown(client, builder) -> None:
    db.session.get(BuilderOption, option_ids(builder, "steak")[0]).is_visible = False
    db.session.commit()
    page = client.get("/fa/build/sandwich").get_data(as_text=True)
    assert "استیک" not in page and "پنیر" in page
    builder.is_visible = False
    db.session.commit()
    assert client.get("/fa/build/sandwich").status_code == 404


def test_sold_out_options_are_shown_but_disabled(client, builder) -> None:
    db.session.get(BuilderOption, option_ids(builder, "steak")[0]).is_in_stock = False
    db.session.commit()
    page = client.get("/fa/build/sandwich").get_data(as_text=True)
    assert "استیک" in page and "disabled" in page


def test_the_no_javascript_form_adds_a_build_to_the_cart(client, builder) -> None:
    ids = option_ids(builder, "baguette", "mayo", "cheese")
    response = client.post(
        "/fa/build/sandwich",
        data={
            "step-1": str(ids[0]),
            "step-2": [str(ids[2])],
            "step-3": str(ids[1]),
            "quantity": "2",
        },
    )
    assert response.status_code == 302 and response.headers["Location"].endswith("/fa/cart")
    assert client.get("/api/cart").get_json()["count"] == 2


def test_the_no_javascript_form_reports_a_refused_build(client, builder) -> None:
    ids = option_ids(builder, "baguette")
    response = client.post("/fa/build/sandwich", data={"step-1": str(ids[0]), "quantity": "1"})
    assert response.status_code == 302 and response.headers["Location"].endswith(
        "/fa/build/sandwich"
    )
    assert client.get("/api/cart").get_json()["count"] == 0


def test_the_cart_checkout_and_order_pages_show_the_chosen_options(client, builder) -> None:
    ids = option_ids(builder, "baguette", "cheese", "mayo")
    add_custom(client, "sandwich", ids)
    assert "پنیر" in client.get("/fa/checkout").get_data(as_text=True)
    response = client.post(
        "/fa/checkout",
        data={
            "customer_name": "Ali",
            "customer_phone": "09123456789",
            "fulfillment": "takeaway",
            "payment_method": "cash_on_site",
        },
    )
    assert response.status_code == 302
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "ساندویچ دلخواه" in page and "پنیر" in page


def test_the_cart_can_be_read_from_the_service_factory(app, builder) -> None:
    with app.test_request_context():
        cart = make_cart_service()
        cart.add_custom(CustomBuild(builder.id, tuple(option_ids(builder, "baguette", "mayo"))), 1)
        assert cart.count() == 1
