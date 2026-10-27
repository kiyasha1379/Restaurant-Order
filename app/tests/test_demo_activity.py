"""The demo's sample contact details, orders and reservations."""

import pytest

from restaurant.constants import OrderStatus, ReservationStatus
from restaurant.extensions import db
from restaurant.models import Order, Reservation
from restaurant.service_factory import (
    make_demo_activity_seeder,
    make_demo_contact_seeder,
    make_demo_seed_service,
    make_settings_admin_service,
    make_translation_service,
)
from tests.helpers import staff_client


@pytest.fixture
def seeded(app):
    make_translation_service().sync_defaults()
    make_demo_seed_service().seed()
    db.session.commit()


def test_sample_activity_covers_several_states(seeded) -> None:
    added = make_demo_activity_seeder().seed()
    db.session.commit()
    assert added == 8
    statuses = {order.status for order in db.session.query(Order)}
    assert {OrderStatus.PLACED, OrderStatus.PREPARING, OrderStatus.READY} <= statuses
    assert OrderStatus.COMPLETED in statuses
    bookings = db.session.query(Reservation).all()
    assert len(bookings) == 3 and len({b.table_id for b in bookings}) == 3
    assert {b.status for b in bookings} == {ReservationStatus.CONFIRMED, ReservationStatus.PENDING}


def test_sample_activity_is_added_only_once(seeded) -> None:
    make_demo_activity_seeder().seed()
    db.session.commit()
    assert make_demo_activity_seeder().seed() == 0
    assert db.session.query(Order).count() == 5


def test_sample_activity_never_piles_onto_real_orders(seeded) -> None:
    make_demo_activity_seeder().seed()
    db.session.commit()
    db.session.query(Order).delete()
    db.session.commit()
    assert make_demo_activity_seeder().seed() == 0  # the bookings still exist


def test_without_dishes_nothing_is_added(app) -> None:
    assert make_demo_activity_seeder().seed() == 0


def test_the_dashboard_and_board_show_the_sample_data(app, seeded) -> None:
    make_demo_activity_seeder().seed()
    db.session.commit()
    manager = staff_client(app, "manager")
    assert manager.get("/admin/dashboard").status_code == 200
    assert manager.get("/admin/orders").status_code == 200
    assert manager.get("/admin/reservations").status_code == 200


def test_contact_placeholders_are_replaced_once_and_edits_are_kept(app) -> None:
    make_translation_service().sync_defaults()
    db.session.commit()
    assert make_demo_contact_seeder().seed() == 3
    db.session.commit()
    contact = make_settings_admin_service().load().contact
    assert contact.phone == "021-12345678" and "ولیعصر" in contact.address["fa"]
    assert make_demo_contact_seeder().seed() == 0
    page = app.test_client().get("/en/").get_data(as_text=True)
    assert "021-12345678" in page and "Valiasr" in page
