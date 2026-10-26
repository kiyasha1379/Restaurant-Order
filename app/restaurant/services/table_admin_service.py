"""Changing the tables of the hall from the admin panel."""

from dataclasses import dataclass
from datetime import datetime

from restaurant.models import DiningTable
from restaurant.repositories import ReservationRepository, TableRepository

MAX_LABEL_LENGTH = 20
MAX_CAPACITY = 50
MOVE_UP = -1
MOVE_DOWN = 1


class TableAdminError(ValueError):
    """A table change was refused."""


class InvalidTableError(TableAdminError):
    """The label is empty or too long, or the capacity is outside 1 to 50."""


class DuplicateTableLabelError(TableAdminError):
    """Another table already uses this label."""


class TableInUseError(TableAdminError):
    """The table still has bookings that have not ended; cancel or move them first."""


@dataclass(frozen=True)
class TableInput:
    """Everything the table form collects."""

    label: str
    capacity: int
    sort_order: int = 0
    is_active: bool = True


class TableAdminService:
    """Creates, changes and removes tables. The caller commits."""

    def __init__(
        self, table_repository: TableRepository, reservation_repository: ReservationRepository
    ) -> None:
        """Receive the repositories instead of importing them, so tests can swap them."""
        self._tables = table_repository
        self._reservations = reservation_repository

    def list_tables(self) -> list[DiningTable]:
        """Return every table (inactive ones too) in floor-plan order."""
        return self._tables.list_ordered()

    def get_table(self, table_id: int) -> DiningTable | None:
        """Return the table with this id, or None."""
        return self._tables.get(table_id)

    def count_upcoming(self, table: DiningTable, now: datetime) -> int:
        """Return how many live bookings (waiting or confirmed) have not ended on this table."""
        return len(self._reservations.list_for_table_from(table.id, now))

    def create_table(self, data: TableInput) -> DiningTable:
        """Add a table. Raises InvalidTableError or DuplicateTableLabelError."""
        table = DiningTable()
        self._apply(table, data)
        return self._tables.add(table)

    def update_table(self, table: DiningTable, data: TableInput) -> DiningTable:
        """Change a table. Existing bookings keep the label they were made with."""
        self._apply(table, data)
        return table

    def delete_table(self, table: DiningTable, now: datetime) -> None:
        """Remove a table. Raises TableInUseError while live bookings are still ahead."""
        if self.count_upcoming(table, now):
            raise TableInUseError(table.label)
        self._tables.delete(table)

    def set_active(self, table: DiningTable, is_active: bool) -> None:
        """Open a table for booking or take it out of use."""
        table.is_active = is_active

    def move_table(self, table: DiningTable, direction: int) -> None:
        """Move a table one place earlier (-1) or later (+1) on the floor plan."""
        ordered = self._tables.list_ordered()
        for position, row in enumerate(ordered):
            row.sort_order = position
        index = ordered.index(table)
        neighbour = index + direction
        if 0 <= neighbour < len(ordered):
            ordered[index].sort_order, ordered[neighbour].sort_order = neighbour, index

    def _apply(self, table: DiningTable, data: TableInput) -> None:
        """Check the values and copy them onto the table."""
        label = (data.label or "").strip()
        if not label or len(label) > MAX_LABEL_LENGTH or not 1 <= data.capacity <= MAX_CAPACITY:
            raise InvalidTableError(label)
        other = self._tables.get_by_label(label)
        if other is not None and other is not table:
            raise DuplicateTableLabelError(label)
        table.label = label
        table.capacity = data.capacity
        table.sort_order = data.sort_order
        table.is_active = data.is_active
