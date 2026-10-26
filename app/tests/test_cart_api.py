"""The cart and quote JSON endpoints."""

import pytest

from restaurant import create_app
from restaurant.extensions import db
from tests.helpers import add_category, add_dish


@pytest.fixture
def dishes(app):
    category = add_category("a", {"fa": "الف", "en": "A"})
    first = add_dish(category, {"fa": "کباب", "en": "Kebab"}, base_price=280_000)
    second = add_dish(category, {"fa": "دوغ", "en": "Doogh"}, base_price=35_000)
    db.session.commit()
    return first.id, second.id


def add(client, dish_id, quantity=1, **query):
    return client.post(
        "/api/cart/add", json={"dish_id": dish_id, "quantity": quantity}, query_string=query
    )


def test_empty_cart(client):
    data = client.get("/api/cart").get_json()
    assert data["count"] == 0 and data["lines"] == [] and data["total"] == 0


def test_adding_returns_the_priced_cart(client, dishes):
    kebab, doogh = dishes
    add(client, kebab, 2)
    data = add(client, doogh).get_json()
    assert data["count"] == 3
    assert [line["line_total"] for line in data["lines"]] == [560_000, 35_000]
    assert data["subtotal"] == 595_000


def test_cart_is_kept_in_the_session_between_requests(client, dishes):
    add(client, dishes[0], 2)
    assert client.get("/api/cart").get_json()["count"] == 2


def test_two_visitors_have_separate_carts(app, dishes):
    first, second = app.test_client(), app.test_client()
    add(first, dishes[0])
    assert second.get("/api/cart").get_json()["count"] == 0


def test_update_changes_and_removes_lines(client, dishes):
    add(client, dishes[0])
    line_id = f"dish-{dishes[0]}"
    assert (
        client.post("/api/cart/update", json={"line_id": line_id, "quantity": 4}).get_json()[
            "count"
        ]
        == 4
    )
    assert (
        client.post("/api/cart/update", json={"line_id": line_id, "quantity": 0}).get_json()[
            "count"
        ]
        == 0
    )


def test_the_browser_cannot_set_a_price(client, dishes):
    data = client.post(
        "/api/cart/add", json={"dish_id": dishes[0], "quantity": 1, "price": 1, "unit_price": 1}
    ).get_json()
    assert data["lines"][0]["unit_price"] == 280_000


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"dish_id": "1"},
        {"dish_id": 0},
        {"dish_id": True},
        {"dish_id": "FIRST", "quantity": 0},
        {"dish_id": "FIRST", "quantity": 99},
        {"dish_id": "FIRST", "quantity": "2"},
    ],
)
def test_bad_add_requests_are_rejected(client, dishes, body):
    body = {**body}
    if body.get("dish_id") == "FIRST":
        body["dish_id"] = dishes[0]
    response = client.post("/api/cart/add", json=body)
    assert response.status_code in (400, 409)
    assert "error" in response.get_json()


def test_bad_update_requests_are_rejected(client, dishes):
    add(client, dishes[0])
    for body in (
        {},
        {"line_id": 5, "quantity": 1},
        {"line_id": "dish-77", "quantity": 1},
        {"line_id": f"dish-{dishes[0]}", "quantity": -3},
    ):
        assert client.post("/api/cart/update", json=body).status_code == 400


def test_unorderable_dishes_cannot_be_added(client, dishes):
    from restaurant.models import Dish

    db.session.get(Dish, dishes[1]).is_in_stock = False
    db.session.commit()
    assert add(client, dishes[1]).status_code == 409
    assert add(client, 12345).status_code == 409


def test_a_dish_that_disappears_is_dropped_from_the_cart(client, dishes):
    from restaurant.models import Dish

    add(client, dishes[0])
    add(client, dishes[1])
    db.session.get(Dish, dishes[1]).is_visible = False
    db.session.commit()
    data = client.get("/api/cart").get_json()
    assert data["count"] == 1 and data["removed_unavailable"] is True
    assert client.get("/api/cart").get_json()["removed_unavailable"] is False


def test_quote_prices_the_chosen_way_of_receiving(client, dishes):
    add(client, dishes[0])
    takeaway = client.get("/api/quote?fulfillment=takeaway").get_json()
    delivery = client.get("/api/quote?fulfillment=delivery").get_json()
    assert takeaway["delivery_fee"] == 0 and takeaway["total"] == 280_000
    assert delivery["delivery_fee"] == 30_000 and delivery["total"] == 310_000


def test_quote_rejects_unknown_fulfillment(client):
    assert client.get("/api/quote?fulfillment=teleport").status_code == 400


def test_names_and_errors_follow_the_language_parameter(client, dishes):
    english = add(client, dishes[0], lang="en").get_json()
    assert english["lines"][0]["name"] == "Kebab"
    assert client.get("/api/cart?lang=fa").get_json()["lines"][0]["name"] == "کباب"
    message = client.post("/api/cart/add?lang=en", json={}).get_json()["error"]
    assert "could not be updated" in message
    assert "به‌روز نشد" in client.post("/api/cart/add?lang=fa", json={}).get_json()["error"]


def test_writes_need_the_csrf_token_when_protection_is_on(dishes):
    app = create_app("test", {"WTF_CSRF_ENABLED": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
    with app.app_context():
        db.create_all()
        client = app.test_client()
        assert client.post("/api/cart/add", json={"dish_id": 1}).status_code == 400
        db.drop_all()


def test_header_badge_counts_items(client, dishes):
    add(client, dishes[0], 3)
    html = client.get("/fa/menu").get_data(as_text=True)
    assert "data-cart-count><bdi>۳</bdi>" in html
