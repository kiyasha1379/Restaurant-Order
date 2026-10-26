"""Queries for categories and dishes."""

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from restaurant.models import (
    Category,
    CategoryTranslation,
    Dish,
    DishTranslation,
    Language,
)
from restaurant.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """Reads menu categories."""

    model = Category

    def list_visible(self) -> list[Category]:
        """Return visible categories in menu order, with their names loaded."""
        statement = (
            select(Category)
            .where(Category.is_visible.is_(True))
            .options(selectinload(Category.translations))
            .order_by(Category.sort_order, Category.id)
        )
        return list(self._session.scalars(statement))

    def get_by_slug(self, slug: str) -> Category | None:
        """Return the category with this slug, or None."""
        return self._session.scalar(select(Category).where(Category.slug == slug))

    def list_all_ordered(self) -> list[Category]:
        """Return every category (hidden ones too) in menu order, with names and dishes loaded."""
        statement = (
            select(Category)
            .options(selectinload(Category.translations), selectinload(Category.dishes))
            .order_by(Category.sort_order, Category.id)
        )
        return list(self._session.scalars(statement))

    def count_without_translation(self, language_code: str) -> int:
        """Return how many categories have no non-empty name in this language."""
        translated = (
            select(CategoryTranslation.category_id)
            .join(Language, Language.id == CategoryTranslation.language_id)
            .where(Language.code == language_code, CategoryTranslation.name != "")
        )
        statement = select(func.count(Category.id)).where(Category.id.not_in(translated))
        return self._session.scalar(statement) or 0

    def delete(self, category: Category) -> None:
        """Stage the removal of a category. The caller commits."""
        self._session.delete(category)


class DishRepository(BaseRepository[Dish]):
    """Reads dishes for the public menu."""

    model = Dish

    def list_visible(self, category_slug: str | None = None) -> list[Dish]:
        """Return visible dishes (optionally of one category) in menu order."""
        statement = self._visible_dishes()
        if category_slug is not None:
            statement = statement.where(Category.slug == category_slug)
        return list(self._session.scalars(statement))

    def list_chefs_picks(self, limit: int) -> list[Dish]:
        """Return up to `limit` visible dishes the chef marked as a pick."""
        statement = self._visible_dishes().where(Dish.is_chefs_pick.is_(True)).limit(limit)
        return list(self._session.scalars(statement))

    def get_many(self, dish_ids: list[int]) -> dict[int, Dish]:
        """Return the dishes with these ids (any visibility), keyed by id, with texts loaded."""
        if not dish_ids:
            return {}
        statement = (
            select(Dish)
            .where(Dish.id.in_(dish_ids))
            .options(selectinload(Dish.translations), selectinload(Dish.images))
        )
        return {dish.id: dish for dish in self._session.scalars(statement)}

    def list_for_admin(self, category_id: int | None = None) -> list[Dish]:
        """Return every dish (hidden ones too), optionally of one category, in menu order."""
        statement = (
            select(Dish)
            .join(Category, Dish.category_id == Category.id)
            .options(selectinload(Dish.translations), selectinload(Dish.images))
            .order_by(Category.sort_order, Dish.sort_order, Dish.id)
        )
        if category_id is not None:
            statement = statement.where(Dish.category_id == category_id)
        return list(self._session.scalars(statement))

    def list_in_category(self, category_id: int) -> list[Dish]:
        """Return the dishes of one category in their current order."""
        statement = (
            select(Dish).where(Dish.category_id == category_id).order_by(Dish.sort_order, Dish.id)
        )
        return list(self._session.scalars(statement))

    def delete(self, dish: Dish) -> None:
        """Stage the removal of a dish. The caller commits."""
        self._session.delete(dish)

    def count_out_of_stock(self) -> int:
        """Return how many dishes on the menu are marked out of stock."""
        statement = select(func.count(Dish.id)).where(
            Dish.is_visible.is_(True), Dish.is_in_stock.is_(False)
        )
        return self._session.scalar(statement) or 0

    def count_without_translation(self, language_code: str) -> int:
        """Return how many dishes have no non-empty name in this language."""
        translated = (
            select(DishTranslation.dish_id)
            .join(Language, Language.id == DishTranslation.language_id)
            .where(Language.code == language_code, DishTranslation.name != "")
        )
        statement = select(func.count(Dish.id)).where(Dish.id.not_in(translated))
        return self._session.scalar(statement) or 0

    @staticmethod
    def _visible_dishes():  # noqa: ANN205 - a SQLAlchemy select statement
        """Build the base query: visible dish in a visible category, texts and photos loaded."""
        return (
            select(Dish)
            .join(Category, Dish.category_id == Category.id)
            .where(Dish.is_visible.is_(True), Category.is_visible.is_(True))
            .options(selectinload(Dish.translations), selectinload(Dish.images))
            .order_by(Category.sort_order, Dish.sort_order, Dish.id)
        )
