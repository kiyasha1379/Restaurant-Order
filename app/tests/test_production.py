"""Production settings, security headers, the backup command and reset-demo."""

import sqlite3
from datetime import datetime

import pytest

from restaurant import create_app
from restaurant.backup import backup_database, prune_backups
from restaurant.extensions import db
from restaurant.hardening import UnsafeConfigurationError
from restaurant.models import Order, Setting, User

GOOD_KEY = "k" * 40


def prod_app(**overrides):
    base = {"SECRET_KEY": GOOD_KEY, "SQLALCHEMY_DATABASE_URI": "sqlite://", "LOG_TO_FILE": False}
    return create_app("prod", base | overrides)


# Settings that must stop the start-up ----------------------------------------------------


@pytest.mark.parametrize("key", ["", "dev-only-secret-change-me", "short"])
def test_weak_secret_keys_are_refused(key) -> None:
    with pytest.raises(UnsafeConfigurationError, match="SECRET_KEY"):
        prod_app(SECRET_KEY=key)


def test_the_mock_gateway_is_refused_in_production() -> None:
    with pytest.raises(UnsafeConfigurationError, match="mock"):
        prod_app(PAYMENT_GATEWAY="mock")


def test_demo_mode_is_refused_in_production() -> None:
    with pytest.raises(UnsafeConfigurationError, match="DEMO_MODE"):
        prod_app(DEMO_MODE=True)


def test_a_good_production_app_starts_with_safe_defaults() -> None:
    app = prod_app()
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["PAYMENT_GATEWAY"] == ""
    assert app.config["DEMO_MODE"] is False


def test_other_configurations_still_start_without_a_key() -> None:
    assert create_app("demo", {"SQLALCHEMY_DATABASE_URI": "sqlite://", "LOG_TO_FILE": False})


# Headers and proxy -------------------------------------------------------------------


def test_every_response_carries_the_basic_security_headers(client) -> None:
    headers = client.get("/fa/").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "Strict-Transport-Security" not in headers  # test config sends no HSTS


def test_production_sends_hsts_and_trusts_one_proxy() -> None:
    app = prod_app()
    with app.app_context():
        db.create_all()
    client = app.test_client()
    response = client.get(
        "/fa/",
        headers={"X-Forwarded-Proto": "https", "X-Forwarded-For": "203.0.113.9"},
        base_url="https://shop.example.ir",
    )
    assert "max-age=" in response.headers["Strict-Transport-Security"]


# Backups ----------------------------------------------------------------------------


def make_database(path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("create table t (v text)")
        connection.execute("insert into t values ('kebab')")


def test_backup_is_a_readable_copy_and_old_ones_are_pruned(tmp_path) -> None:
    source = tmp_path / "live.db"
    make_database(source)
    folder = tmp_path / "backups"
    paths = [
        backup_database(source, folder, datetime(2026, 10, day, 3, 30), keep=2) for day in (1, 2, 3)
    ]
    assert sorted(path.name for path in folder.iterdir()) == [p.name for p in paths[1:]]
    with sqlite3.connect(paths[-1]) as copy:
        assert copy.execute("select v from t").fetchone() == ("kebab",)


def test_backup_of_a_missing_database_says_so(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        backup_database(tmp_path / "nope.db", tmp_path / "b", datetime(2026, 1, 1), keep=3)


def test_prune_always_keeps_at_least_one(tmp_path) -> None:
    for name in ("restaurant-1.db", "restaurant-2.db"):
        (tmp_path / name).write_bytes(b"x")
    prune_backups(tmp_path, keep=0)
    assert [path.name for path in tmp_path.iterdir()] == ["restaurant-2.db"]


def test_backup_command_writes_into_the_chosen_folder(tmp_path) -> None:
    source = tmp_path / "live.db"
    make_database(source)
    uri = f"sqlite:///{source}"
    overrides = {"SQLALCHEMY_DATABASE_URI": uri, "UPLOAD_FOLDER": tmp_path / "u"}
    app = create_app("test", overrides)
    with app.app_context():
        result = app.test_cli_runner().invoke(
            args=["backup-db", "--to", str(tmp_path / "out"), "--keep", "3"]
        )
    assert result.exit_code == 0, result.output
    assert len(list((tmp_path / "out").glob("restaurant-*.db"))) == 1


# reset-demo ----------------------------------------------------------------------------


def test_reset_demo_refuses_outside_demo_mode(app) -> None:
    result = app.test_cli_runner().invoke(args=["reset-demo", "--yes"])
    assert result.exit_code != 0 and "APP_CONFIG=demo" in result.output


def test_reset_demo_wipes_everything_and_reseeds(tmp_path) -> None:
    app = create_app(
        "demo",
        {
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "LOG_TO_FILE": False,
            "UPLOAD_FOLDER": tmp_path / "uploads",
        },
    )
    runner = app.test_cli_runner()
    with app.app_context():
        db.create_all()
        from tests.conftest import add_two_languages

        add_two_languages()
        assert runner.invoke(args=["seed-demo"]).exit_code == 0
        db.session.add(Setting(key="brand_name", value="Changed"))
        (tmp_path / "uploads" / "site").mkdir(parents=True)
        (tmp_path / "uploads" / "site" / "logo.webp").write_bytes(b"x")
        db.session.commit()
        users_before = db.session.query(User).count()
        orders_before = db.session.query(Order).count()
        assert orders_before > 0

        result = runner.invoke(args=["reset-demo", "--yes"])
        assert result.exit_code == 0, result.output
        assert db.session.get(Setting, "brand_name") is None
        # Sample orders are reseeded, so the count is the sample set, not doubled.
        assert db.session.query(Order).count() == orders_before
        assert db.session.query(User).count() == users_before
        assert not any((tmp_path / "uploads").rglob("*.webp"))
        assert client_ok(app)


def client_ok(app) -> bool:
    return app.test_client().get("/fa/menu").status_code == 200
