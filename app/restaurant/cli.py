"""Command-line commands: `flask seed-demo` and `flask reset-demo`."""

from pathlib import Path

import click
from flask import Flask, current_app
from sqlalchemy import inspect
from sqlalchemy.engine import make_url

from restaurant.backup import backup_database
from restaurant.config import INSTANCE_DIR
from restaurant.extensions import db
from restaurant.seed.demo_reset import DemoWiper
from restaurant.seed.demo_staff import DEMO_STAFF_PASSWORD
from restaurant.service_factory import (
    make_access_service,
    make_demo_activity_seeder,
    make_demo_contact_seeder,
    make_demo_customer_seeder,
    make_demo_seed_service,
    make_demo_staff_seeder,
    make_order_service,
    make_staff_service,
    make_translation_service,
)
from restaurant.services import (
    InvalidTransitionError,
    StaffError,
    WeakPasswordError,
)
from restaurant.timeutils import now_tehran


@click.command("sync-ui-strings")
def sync_ui_strings_command() -> None:
    """Copy default interface texts that are missing from the database (never overwrites)."""
    report = make_translation_service().sync_defaults()
    db.session.commit()
    click.echo(f"sync-ui-strings: added {report.added_keys} keys and {report.added_texts} texts.")


def _seed_everything() -> None:
    """Add the sample data (menu, builders, tables, staff, customer) that is missing."""
    report = make_demo_seed_service().seed()
    db.session.commit()
    click.echo(
        f"seed-demo: added {report.backgrounds} backgrounds, "
        f"{report.categories} categories, {report.dishes} dishes, "
        f"{report.builders} builders and {report.tables} tables."
    )
    staff_added = make_demo_staff_seeder().seed()
    db.session.commit()
    if staff_added:
        click.echo(
            f"seed-demo: added {staff_added} sample staff accounts "
            f"(admin@example.com, manager@, cashier@, kitchen@, viewer@) "
            f"with the password {DEMO_STAFF_PASSWORD}. Use them for the demo only."
        )
    if make_demo_contact_seeder().seed():
        click.echo("seed-demo: filled in sample contact details for the footer.")
    db.session.commit()
    customer_rows = make_demo_customer_seeder().seed()
    db.session.commit()
    activity = make_demo_activity_seeder().seed()
    db.session.commit()
    if activity:
        click.echo(f"seed-demo: added {activity} sample orders and reservations.")
    if customer_rows:
        click.echo(
            "seed-demo: added a sample customer (customer@example.com or 09120000000, "
            f"password {DEMO_STAFF_PASSWORD}) and sample contact messages."
        )


@click.command("seed-demo")
def seed_demo_command() -> None:
    """Add the sample menu and backgrounds for the demo (never changes existing rows)."""
    _seed_everything()


@click.command("create-admin")
@click.option("--email", prompt=True, help="Sign-in e-mail of the new administrator.")
@click.option("--name", "display_name", prompt="Name", help="Name shown in the panel.")
@click.password_option(help="At least 8 characters.")
def create_admin_command(email: str, display_name: str, password: str) -> None:
    """Create an administrator account (also creates the default roles if they are missing)."""
    access_service = make_access_service()
    access_service.ensure_defaults()
    db.session.flush()
    admin_role = next(role for role in make_staff_service().list_roles() if role.is_system)
    try:
        make_staff_service().create_staff(email, display_name, password, [admin_role.id])
    except (StaffError, WeakPasswordError) as error:
        db.session.rollback()
        raise click.ClickException(f"Could not create the account: {error}") from error
    db.session.commit()
    click.echo(f"create-admin: {email.strip().lower()} can now sign in at /admin/login.")


@click.command("advance-order")
@click.argument("order_id", type=int)
def advance_order_command(order_id: int) -> None:
    """Move an order one step forward (demo helper until the admin panel exists)."""
    order_service = make_order_service()
    order = order_service.get(order_id)
    if order is None:
        raise click.ClickException(f"There is no order {order_id}.")
    try:
        order_service.advance(order)
    except InvalidTransitionError as error:
        raise click.ClickException(str(error)) from error
    db.session.commit()
    click.echo(f"advance-order: order {order_id} is now {order.status.value}.")


@click.command("reset-demo")
@click.option("--yes", is_flag=True, help="Do not ask for confirmation.")
def reset_demo_command(yes: bool) -> None:
    """Delete ALL data and uploads, then load the sample data again (demo installations only)."""
    if not current_app.config["DEMO_MODE"]:
        raise click.ClickException(
            "reset-demo only runs with APP_CONFIG=demo; it deletes every order, customer "
            "and setting."
        )
    existing = set(inspect(db.engine).get_table_names())
    missing = {table.name for table in db.metadata.sorted_tables} - existing
    if missing:
        raise click.ClickException("The database is not set up yet. Run `flask db upgrade` first.")
    if not yes:
        click.confirm("This deletes ALL data and uploaded files. Continue?", abort=True)
    wiper = DemoWiper(db.session, db.metadata.sorted_tables, current_app.config["UPLOAD_FOLDER"])
    files = wiper.wipe()
    db.session.commit()
    click.echo(f"reset-demo: emptied the database and removed {files} uploaded files.")
    make_access_service().ensure_defaults()
    db.session.commit()
    sync_ui_strings_command.callback()
    _seed_everything()
    click.echo("reset-demo: done. The demo is back to its starting state.")


@click.command("backup-db")
@click.option("--keep", default=14, show_default=True, help="How many backups to keep.")
@click.option(
    "--to", "target", default=None, help="Folder for the copies (default instance/backups)."
)
def backup_db_command(keep: int, target: str | None) -> None:
    """Save a consistent copy of the database and delete the oldest copies."""
    source = Path(make_url(current_app.config["SQLALCHEMY_DATABASE_URI"]).database or "")
    folder = Path(target) if target else INSTANCE_DIR / "backups"
    path = backup_database(source, folder, now_tehran(), keep)
    click.echo(f"backup-db: saved {path} (keeping the newest {keep}).")


def register_commands(app: Flask) -> None:
    """Attach every custom command to the `flask` command line."""
    app.cli.add_command(sync_ui_strings_command)
    app.cli.add_command(seed_demo_command)
    app.cli.add_command(create_admin_command)
    app.cli.add_command(advance_order_command)
    app.cli.add_command(reset_demo_command)
    app.cli.add_command(backup_db_command)
