"""Column helpers used by more than one model."""

from enum import Enum as PythonEnum

from sqlalchemy import Enum


def enum_type(enum_class: type[PythonEnum]) -> Enum:
    """Store an enum as readable text (its value), not as a native database enum.

    Text keeps SQLite and a later PostgreSQL move simple, and rows stay
    understandable when someone reads the database by hand.
    """
    longest_value = max(len(member.value) for member in enum_class)
    return Enum(
        enum_class,
        native_enum=False,
        length=longest_value,
        values_callable=lambda members: [member.value for member in members],
    )
