"""Command-line commands: `flask seed-demo` and `flask reset-demo`."""

import click
from flask import Flask

from restaurant.extensions import db
from restaurant.seed.demo_staff import DEMO_STAFF_PASSWORD
from restaurant.service_factory import (
    make_access_service,
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


@click.command("sync-ui-strings")
def sync_ui_strings_command() -> None:
    """Copy default interface texts that are missing from the database (never overwrites)."""
    report = make_translation_service().sync_defaults()
    db.session.commit()
    click.echo(f"sync-ui-strings: added {report.added_keys} keys and {report.added_texts} texts.")


@click.command("seed-demo")
def seed_demo_command() -> None:
    """Add the sample menu and backgrounds for the demo (never changes existing rows)."""
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
    customer_rows = make_demo_customer_seeder().seed()
    db.session.commit()
    if customer_rows:
        click.echo(
            "seed-demo: added a sample customer (customer@example.com or 09120000000, "
            f"password {DEMO_STAFF_PASSWORD}) and sample contact messages."
        )


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
def reset_demo_command() -> None:
    """Return the demo to its starting state (filled in by later phases)."""
    click.echo("reset-demo: there is nothing to reset yet. Later phases add it.")


def register_commands(app: Flask) -> None:
    """Attach every custom command to the `flask` command line."""
    app.cli.add_command(sync_ui_strings_command)
    app.cli.add_command(seed_demo_command)
    app.cli.add_command(create_admin_command)
    app.cli.add_command(advance_order_command)
    app.cli.add_command(reset_demo_command)
