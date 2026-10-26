"""The migration builds the same schema the models describe."""

import sqlite3

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask_migrate import upgrade

from restaurant import create_app
from restaurant.extensions import db

EXPECTED_TABLES = {
    "languages",
    "settings",
    "backgrounds",
    "users",
    "roles",
    "permissions",
    "role_permissions",
    "user_roles",
    "categories",
    "category_translations",
    "dishes",
    "dish_translations",
    "orders",
    "order_items",
    "order_item_options",
    "order_status_log",
    "dish_images",
    "ui_strings",
    "ui_string_translations",
}


def build_database(tmp_path):
    """Run `flask db upgrade` on a new file database and return its app and path."""
    database_file = tmp_path / "migrated.db"
    app = create_app("test", {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_file}"})
    with app.app_context():
        upgrade()
    return app, database_file


def test_upgrade_creates_every_table_and_the_two_languages(tmp_path):
    _, database_file = build_database(tmp_path)
    with sqlite3.connect(database_file) as connection:
        tables = {
            row[0]
            for row in connection.execute("select name from sqlite_master where type='table'")
        }
        languages = connection.execute(
            "select code, direction, is_default from languages order by id"
        ).fetchall()
    assert tables >= EXPECTED_TABLES
    assert languages == [("fa", "rtl", 1), ("en", "ltr", 0)]


def test_migration_matches_the_models(tmp_path):
    app, _ = build_database(tmp_path)
    with app.app_context(), db.engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        differences = compare_metadata(context, db.metadata)
    assert differences == []


def test_payments_migration_gives_old_orders_their_payment_row(tmp_path):
    """Orders that exist before the payments table get one pay-on-site row matching their state."""
    database_file = tmp_path / "old.db"
    app = create_app("test", {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_file}"})
    with app.app_context():
        upgrade(revision="2f06b2de0129")
    with sqlite3.connect(database_file) as connection:
        for status in ("placed", "completed", "cancelled"):
            connection.execute(
                "insert into orders (public_token, language_code, customer_name, customer_phone,"
                " fulfillment, delivery_address, note, payment_method, status, subtotal,"
                " delivery_fee, total, created_at, updated_at) values (?, 'fa', 'Ali',"
                " '09123456789', 'takeaway', '', '', 'cash_on_site', ?, 100, 0, 100,"
                " '2026-10-26 12:00:00', '2026-10-26 12:30:00')",
                (f"token-{status}", status),
            )
    with app.app_context():
        upgrade()
    with sqlite3.connect(database_file) as connection:
        rows = connection.execute(
            "select o.status, p.method, p.status, p.amount, p.paid_at is not null"
            " from payments p join orders o on o.id = p.order_id order by o.id"
        ).fetchall()
    assert rows == [
        ("placed", "cash_on_site", "pending", 100, 0),
        ("completed", "cash_on_site", "paid", 100, 1),
        ("cancelled", "cash_on_site", "cancelled", 100, 0),
    ]
