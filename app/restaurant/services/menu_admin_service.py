"""Changing the menu from the admin panel: dishes, categories, photos and their order."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from restaurant.models import Category, CategoryTranslation, Dish, DishImage, DishTranslation
from restaurant.repositories import CategoryRepository, DishRepository, LanguageRepository

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_SLUG_LENGTH = 60
MOVE_UP = -1
MOVE_DOWN = 1


class MenuAdminError(ValueError):
    """A menu change was refused."""


class UnknownCategoryError(MenuAdminError):
    """The chosen category does not exist."""


class DuplicateSlugError(MenuAdminError):
    """Another category already uses this slug."""


class InvalidSlugError(MenuAdminError):
    """The slug is empty or has characters other than a-z, 0-9 and dashes."""


class CategoryNotEmptyError(MenuAdminError):
    """A category that still has dishes cannot be deleted."""


@dataclass(frozen=True)
class DishTexts:
    """The four texts of a dish in one language."""

    name: str = ""
    description: str = ""
    ingredients: str = ""
    serving_note: str = ""

    @property
    def is_blank(self) -> bool:
        """Return True when nothing is written."""
        return not any((self.name, self.description, self.ingredients, self.serving_note))


@dataclass(frozen=True)
class DishInput:
    """Everything the dish form collects. `texts` is keyed by language code."""

    category_id: int
    base_price: int
    sort_order: int = 0
    is_in_stock: bool = True
    is_chefs_pick: bool = False
    is_visible: bool = True
    texts: Mapping[str, DishTexts] = field(default_factory=dict)


@dataclass(frozen=True)
class CategoryInput:
    """Everything the category form collects. `names` is keyed by language code."""

    slug: str
    sort_order: int = 0
    is_visible: bool = True
    names: Mapping[str, str] = field(default_factory=dict)


class MenuAdminService:
    """Creates, changes and removes menu rows. The caller commits."""

    def __init__(
        self,
        category_repository: CategoryRepository,
        dish_repository: DishRepository,
        language_repository: LanguageRepository,
    ) -> None:
        """Receive the repositories instead of importing them, so tests can swap them."""
        self._categories = category_repository
        self._dishes = dish_repository
        self._languages = language_repository

    # --- reading -------------------------------------------------------

    def list_categories(self) -> list[Category]:
        """Return all categories in menu order."""
        return self._categories.list_all_ordered()

    def list_dishes(self, category_id: int | None = None) -> list[Dish]:
        """Return all dishes, optionally of one category, in menu order."""
        return self._dishes.list_for_admin(category_id)

    def get_dish(self, dish_id: int) -> Dish | None:
        """Return the dish with this id, or None."""
        return self._dishes.get(dish_id)

    def get_category(self, category_id: int) -> Category | None:
        """Return the category with this id, or None."""
        return self._categories.get(category_id)

    # --- dishes --------------------------------------------------------

    def create_dish(self, data: DishInput) -> Dish:
        """Add a dish with its texts. Raises UnknownCategoryError."""
        self._require_category(data.category_id)
        dish = Dish()
        self._apply_dish(dish, data)
        return self._dishes.add(dish)

    def update_dish(self, dish: Dish, data: DishInput) -> Dish:
        """Change a dish and its texts. Raises UnknownCategoryError."""
        self._require_category(data.category_id)
        self._apply_dish(dish, data)
        return dish

    def delete_dish(self, dish: Dish) -> list[str]:
        """Remove a dish; return its photo paths so the caller can delete the files."""
        paths = [image.path for image in dish.images]
        self._dishes.delete(dish)
        return paths

    @staticmethod
    def set_in_stock(dish: Dish, in_stock: bool) -> None:
        """Mark a dish as available or sold out."""
        dish.is_in_stock = in_stock

    @staticmethod
    def set_visible(dish: Dish, visible: bool) -> None:
        """Show or hide a dish on the public menu."""
        dish.is_visible = visible

    @staticmethod
    def set_photo(dish: Dish, path: str) -> str | None:
        """Make `path` the dish's photo; return the old photo's path (to delete), if any."""
        if dish.images:
            old_path, dish.images[0].path = dish.images[0].path, path
            return old_path
        dish.images.append(DishImage(path=path, sort_order=0))
        return None

    @staticmethod
    def remove_photo(dish: Dish) -> str | None:
        """Remove the dish's photo; return its path (to delete), if there was one."""
        if not dish.images:
            return None
        removed = dish.images[0]
        dish.images.remove(removed)
        return removed.path

    def move_dish(self, dish: Dish, direction: int) -> None:
        """Move a dish one place up (-1) or down (+1) inside its category."""
        siblings = self._dishes.list_in_category(dish.category_id)
        self._move_within(siblings, dish, direction)

    # --- categories ----------------------------------------------------

    def create_category(self, data: CategoryInput) -> Category:
        """Add a category. Raises InvalidSlugError or DuplicateSlugError."""
        category = Category()
        self._apply_category(category, data)
        return self._categories.add(category)

    def update_category(self, category: Category, data: CategoryInput) -> Category:
        """Change a category. Raises InvalidSlugError or DuplicateSlugError."""
        self._apply_category(category, data)
        return category

    def delete_category(self, category: Category) -> None:
        """Remove an empty category. Raises CategoryNotEmptyError."""
        if category.dishes:
            raise CategoryNotEmptyError(category.slug)
        self._categories.delete(category)

    def move_category(self, category: Category, direction: int) -> None:
        """Move a category one place left (-1) or right (+1) in the menu."""
        self._move_within(self._categories.list_all_ordered(), category, direction)

    # --- helpers -------------------------------------------------------

    def _require_category(self, category_id: int) -> None:
        """Raise UnknownCategoryError unless the category exists."""
        if self._categories.get(category_id) is None:
            raise UnknownCategoryError(str(category_id))

    def _apply_dish(self, dish: Dish, data: DishInput) -> None:
        """Copy the form values onto the dish and its translation rows."""
        dish.category_id = data.category_id
        dish.base_price = data.base_price
        dish.sort_order = data.sort_order
        dish.is_in_stock = data.is_in_stock
        dish.is_chefs_pick = data.is_chefs_pick
        dish.is_visible = data.is_visible
        existing = {row.language.code: row for row in dish.translations}
        for code, texts in data.texts.items():
            row = existing.get(code)
            if texts.is_blank:
                if row is not None:
                    dish.translations.remove(row)
                continue
            if row is None:
                row = DishTranslation(language_id=self._language_id(code))
                dish.translations.append(row)
            row.name = texts.name
            row.description = texts.description
            row.ingredients = texts.ingredients
            row.serving_note = texts.serving_note

    def _apply_category(self, category: Category, data: CategoryInput) -> None:
        """Copy the form values onto the category and its name rows."""
        slug = data.slug.strip().lower()
        if not slug or len(slug) > MAX_SLUG_LENGTH or not SLUG_PATTERN.match(slug):
            raise InvalidSlugError(slug)
        other = self._categories.get_by_slug(slug)
        if other is not None and other is not category:
            raise DuplicateSlugError(slug)
        category.slug = slug
        category.sort_order = data.sort_order
        category.is_visible = data.is_visible
        existing = {row.language.code: row for row in category.translations}
        for code, name in data.names.items():
            row = existing.get(code)
            if not name.strip():
                if row is not None:
                    category.translations.remove(row)
                continue
            if row is None:
                row = CategoryTranslation(language_id=self._language_id(code))
                category.translations.append(row)
            row.name = name.strip()

    def _language_id(self, code: str) -> int:
        """Return the id of the language with this code."""
        language = self._languages.get_by_code(code)
        if language is None:
            raise MenuAdminError(f"Unknown language {code}")
        return language.id

    @staticmethod
    def _move_within(ordered: list, item, direction: int) -> None:  # noqa: ANN001 - any ordered row
        """Renumber `ordered` 0..n-1, then swap `item` with its neighbour in `direction`."""
        for position, row in enumerate(ordered):
            row.sort_order = position
        index = ordered.index(item)
        neighbour = index + direction
        if 0 <= neighbour < len(ordered):
            ordered[index].sort_order, ordered[neighbour].sort_order = neighbour, index
