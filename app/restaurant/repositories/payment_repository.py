"""Queries for payments."""

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from restaurant.models import Payment
from restaurant.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    """Reads and stores payment attempts."""

    model = Payment

    def get_by_authority(self, authority: str) -> Payment | None:
        """Return the attempt the gateway knows under this reference, or None."""
        if not authority:
            return None
        statement = (
            select(Payment).where(Payment.authority == authority).options(joinedload(Payment.order))
        )
        return self._session.scalar(statement)
