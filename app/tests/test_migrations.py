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
