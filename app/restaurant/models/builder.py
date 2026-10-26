"""Builder tables: a builder (pizza, sandwich, drink...) has steps, and a step has options.

One generic model serves every kind, so a new kind of build needs no code change
(technical plan, section 4). Names live in translation tables; prices are whole tomans.
"""

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from restaurant.constants import PreviewKind
from restaurant.extensions import db
from restaurant.models.columns import enum_type
from restaurant.models.mixins import TranslationMixin


class Builder(db.Model):
    """One kind of custom build. `key` is the address part: /fa/build/<key>."""

    __tablename__ = "builders"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True)
    preview_kind: Mapped[PreviewKind] = mapped_column(
        enum_type(PreviewKind), default=PreviewKind.PLAIN
    )
    sort_order: Mapped[int] = mapped_column(default=0)
    is_visible: Mapped[bool] = mapped_column(default=True)

    translations: Mapped[list["BuilderTranslation"]] = relationship(
        back_populates="builder", cascade="all, delete-orphan"
    )
    steps: Mapped[list["BuilderStep"]] = relationship(
        back_populates="builder",
        cascade="all, delete-orphan",
        order_by="BuilderStep.sort_order, BuilderStep.id",
    )


class BuilderTranslation(TranslationMixin, db.Model):
    """A builder name and a one-line hint in one language."""

    __tablename__ = "builder_translations"

    builder_id: Mapped[int] = mapped_column(
        ForeignKey("builders.id", ondelete="CASCADE"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String(120))
    hint: Mapped[str] = mapped_column(String(255), default="")

    builder: Mapped[Builder] = relationship(back_populates="translations")


class BuilderStep(db.Model):
    """A step such as "size" or "toppings".

    `is_base`: the options' prices are shown in full, not as "+price" (a size or a bread).
    `is_layered`: the customer may reorder the chosen options (sandwich layers).
    `preview_role`: what the step draws in the picture (see `PreviewRole`).
    """

    __tablename__ = "builder_steps"
    __table_args__ = (UniqueConstraint("builder_id", "key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    builder_id: Mapped[int] = mapped_column(ForeignKey("builders.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(40))
    sort_order: Mapped[int] = mapped_column(default=0)
    is_multiple: Mapped[bool] = mapped_column(default=False)
    is_required: Mapped[bool] = mapped_column(default=True)
    is_base: Mapped[bool] = mapped_column(default=False)
    is_layered: Mapped[bool] = mapped_column(default=False)
    preview_role: Mapped[str] = mapped_column(String(20), default="")

    builder: Mapped[Builder] = relationship(back_populates="steps")
    translations: Mapped[list["BuilderStepTranslation"]] = relationship(
        back_populates="step", cascade="all, delete-orphan"
    )
    options: Mapped[list["BuilderOption"]] = relationship(
        back_populates="step",
        cascade="all, delete-orphan",
        order_by="BuilderOption.sort_order, BuilderOption.id",
    )


class BuilderStepTranslation(TranslationMixin, db.Model):
    """A step title and a short hint in one language."""

    __tablename__ = "builder_step_translations"

    step_id: Mapped[int] = mapped_column(
        ForeignKey("builder_steps.id", ondelete="CASCADE"), primary_key=True
    )
    title: Mapped[str] = mapped_column(String(120))
    hint: Mapped[str] = mapped_column(String(255), default="")

    step: Mapped[BuilderStep] = relationship(back_populates="translations")


class BuilderOption(db.Model):
    """One choice in a step, with its price and how it looks in the picture.

    `color` and `shape` draw the placeholder; `preview_amount` is a size in the picture
    (layer thickness, liquid level...); `layer_image` replaces the placeholder with a photo.
    """

    __tablename__ = "builder_options"
    __table_args__ = (
        UniqueConstraint("step_id", "key"),
        CheckConstraint("price >= 0", name="price_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    step_id: Mapped[int] = mapped_column(ForeignKey("builder_steps.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(40))
    price: Mapped[int] = mapped_column(default=0)
    sort_order: Mapped[int] = mapped_column(default=0)
    is_in_stock: Mapped[bool] = mapped_column(default=True)
    is_visible: Mapped[bool] = mapped_column(default=True)
    color: Mapped[str] = mapped_column(String(9), default="")
    shape: Mapped[str] = mapped_column(String(20), default="")
    preview_amount: Mapped[int] = mapped_column(default=0)
    layer_image: Mapped[str | None] = mapped_column(String(255))

    step: Mapped[BuilderStep] = relationship(back_populates="options")
    translations: Mapped[list["BuilderOptionTranslation"]] = relationship(
        back_populates="option", cascade="all, delete-orphan"
    )


class BuilderOptionTranslation(TranslationMixin, db.Model):
    """An option name in one language."""

    __tablename__ = "builder_option_translations"

    option_id: Mapped[int] = mapped_column(
        ForeignKey("builder_options.id", ondelete="CASCADE"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String(120))
    note: Mapped[str] = mapped_column(Text, default="")

    option: Mapped[BuilderOption] = relationship(back_populates="translations")
