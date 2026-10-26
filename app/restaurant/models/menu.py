"""Menu tables: categories, dishes, their translations and photos.

Money is stored as whole tomans. Names and descriptions live in the
translation tables so both languages are edited from the admin panel.
"""

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from restaurant.extensions import db
from restaurant.models.mixins import TranslationMixin


class Category(db.Model):
    """A menu group such as pizza, sandwich or drinks."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    is_visible: Mapped[bool] = mapped_column(default=True)

    translations: Mapped[list["CategoryTranslation"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )
    dishes: Mapped[list["Dish"]] = relationship(back_populates="category")


class CategoryTranslation(TranslationMixin, db.Model):
    """A category name in one language."""

    __tablename__ = "category_translations"

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String(120))

    category: Mapped[Category] = relationship(back_populates="translations")


class Dish(db.Model):
    """A dish on the menu. `base_price` is the price before any builder options."""

    __tablename__ = "dishes"
    __table_args__ = (CheckConstraint("base_price >= 0", name="base_price_not_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    base_price: Mapped[int] = mapped_column(default=0)
    is_in_stock: Mapped[bool] = mapped_column(default=True)
    is_chefs_pick: Mapped[bool] = mapped_column(default=False)
    is_visible: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(default=0)

    category: Mapped[Category] = relationship(back_populates="dishes")
    translations: Mapped[list["DishTranslation"]] = relationship(
        back_populates="dish", cascade="all, delete-orphan"
    )
    images: Mapped[list["DishImage"]] = relationship(
        back_populates="dish", cascade="all, delete-orphan", order_by="DishImage.sort_order"
    )


class DishTranslation(TranslationMixin, db.Model):
    """A dish name, description, ingredients and serving note in one language."""

    __tablename__ = "dish_translations"

    dish_id: Mapped[int] = mapped_column(
        ForeignKey("dishes.id", ondelete="CASCADE"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    # Shown on the back of the round dish card.
    ingredients: Mapped[str] = mapped_column(Text, default="")
    serving_note: Mapped[str] = mapped_column(String(120), default="")

    dish: Mapped[Dish] = relationship(back_populates="translations")


class DishImage(db.Model):
    """A photo of a dish. Placeholders are data too, so swapping needs no code change."""

    __tablename__ = "dish_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    dish_id: Mapped[int] = mapped_column(ForeignKey("dishes.id", ondelete="CASCADE"))
    path: Mapped[str] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(default=0)

    dish: Mapped[Dish] = relationship(back_populates="images")
