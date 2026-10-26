"""Interface texts that the admin panel can edit, one row per key and language."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from restaurant.extensions import db
from restaurant.models.mixins import TranslationMixin


class UiString(db.Model):
    """A named piece of interface text, such as 'home.headline'."""

    __tablename__ = "ui_strings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(120), unique=True)

    translations: Mapped[list["UiStringTranslation"]] = relationship(
        back_populates="ui_string", cascade="all, delete-orphan"
    )


class UiStringTranslation(TranslationMixin, db.Model):
    """The text of one interface string in one language."""

    __tablename__ = "ui_string_translations"

    ui_string_id: Mapped[int] = mapped_column(
        ForeignKey("ui_strings.id", ondelete="CASCADE"), primary_key=True
    )
    text: Mapped[str] = mapped_column(Text, default="")

    ui_string: Mapped[UiString] = relationship(back_populates="translations")
