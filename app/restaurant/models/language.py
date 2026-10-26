"""The `languages` table: exactly two rows, Persian and English."""

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from restaurant.constants import SUPPORTED_LANGUAGE_CODES, TextDirection
from restaurant.extensions import db
from restaurant.models.columns import enum_type


def _quoted_codes() -> str:
    """Return the supported codes as an SQL list: 'fa', 'en'."""
    return ", ".join(f"'{code}'" for code in SUPPORTED_LANGUAGE_CODES)


class Language(db.Model):
    """One site language. English can be switched off; Persian is the fallback."""

    __tablename__ = "languages"
    __table_args__ = (
        # A third language is not a feature of the application (plan, section 7).
        CheckConstraint(f"code IN ({_quoted_codes()})", name="supported_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(5), unique=True)
    name: Mapped[str] = mapped_column(String(50))
    direction: Mapped[TextDirection] = mapped_column(enum_type(TextDirection))
    is_default: Mapped[bool] = mapped_column(default=False)
    is_enabled: Mapped[bool] = mapped_column(default=True)

    def __repr__(self) -> str:
        """Short representation for logs and the debugger."""
        return f"<Language {self.code}>"
