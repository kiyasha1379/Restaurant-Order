"""Generic repository: the only place that talks to the session for one table."""

from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Basic reads and writes shared by every repository.

    Services never write queries (plan, section 2); they call a repository,
    which receives the session through its constructor so tests can replace it.
    """

    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        """Keep the session this repository works with."""
        self._session = session

    def get(self, primary_key: object) -> ModelT | None:
        """Return the row with this primary key, or None."""
        return self._session.get(self.model, primary_key)

    def list_all(self) -> list[ModelT]:
        """Return every row of the table."""
        return list(self._session.scalars(select(self.model)))

    def count(self) -> int:
        """Return how many rows the table has."""
        return self._session.scalar(select(func.count()).select_from(self.model)) or 0

    def add(self, entity: ModelT) -> ModelT:
        """Stage a new row. The caller decides when to commit."""
        self._session.add(entity)
        return entity

    def refresh(self, entity: ModelT) -> None:
        """Reload the row from the database, discarding what the session remembers."""
        self._session.refresh(entity)

    def flush(self) -> None:
        """Send staged changes to the database without committing (gives new rows their ids)."""
        self._session.flush()
