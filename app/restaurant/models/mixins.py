"""Reusable column groups shared by several models (no repeated columns)."""

from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from restaurant.timeutils import now_tehran


class TimestampMixin:
    """Adds `created_at` and `updated_at`, both in Tehran time."""

    created_at: Mapped[datetime] = mapped_column(default=now_tehran)
    updated_at: Mapped[datetime] = mapped_column(default=now_tehran, onupdate=now_tehran)


class TranslationMixin:
    """Turns a model into one language's text for a parent row.

    Every translatable text lives in a `*_translations` table (plan, section 4).
    A subclass adds its parent key as part of the primary key and its own text
    columns; the language key is declared here once.
    """

    @declared_attr
    def language_id(cls) -> Mapped[int]:  # noqa: N805 - SQLAlchemy convention
        """Foreign key to the language this text is written in."""
        return mapped_column(ForeignKey("languages.id", ondelete="CASCADE"), primary_key=True)

    @declared_attr
    def language(cls) -> Mapped["Language"]:  # noqa: N805,F821 - SQLAlchemy convention
        """Load the language row together with the text, so its code is at hand."""
        return relationship("Language", lazy="joined")


class SnapshotNameMixin:
    """Adds `name_in` to rows that store a Persian and an English name copied at order time."""

    name_fa: str
    name_en: str

    def name_in(self, language_code: str) -> str:
        """Return the snapshot name in a language, falling back to Persian."""
        return (self.name_en if language_code == "en" else self.name_fa) or self.name_fa
