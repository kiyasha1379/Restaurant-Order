"""The public menu: categories and dishes written in the visitor's language."""

from dataclasses import dataclass

from restaurant.models import Dish
from restaurant.repositories import CategoryRepository, DishRepository
from restaurant.services.localized import pick_translation


@dataclass(frozen=True)
class CategoryView:
    """A category as a template needs it."""

    slug: str
    name: str


@dataclass(frozen=True)
class DishView:
    """A dish in one language, safe to keep after the database session ends."""

    id: int
    category_slug: str
    name: str
    description: str
    ingredients: str
    serving_note: str
    price: int
    image_path: str | None
    is_in_stock: bool


class MenuService:
    """Builds menu views, falling back to Persian when a translation is missing."""

    def __init__(
        self, category_repository: CategoryRepository, dish_repository: DishRepository
    ) -> None:
        """Receive the repositories instead of importing them, so tests can swap them."""
        self._category_repository = category_repository
        self._dish_repository = dish_repository

    def list_categories(self, language_code: str) -> list[CategoryView]:
        """Return the visible categories in menu order."""
        views = []
        for category in self._category_repository.list_visible():
            translation = pick_translation(category.translations, language_code)
            views.append(
                CategoryView(
                    slug=category.slug, name=translation.name if translation else category.slug
                )
            )
        return views

    def list_dishes(self, language_code: str, category_slug: str | None = None) -> list[DishView]:
        """Return visible dishes, all of them or only one category's."""
        dishes = self._dish_repository.list_visible(category_slug)
        return [self._to_view(dish, language_code) for dish in dishes]

    def list_chefs_picks(self, language_code: str, limit: int = 4) -> list[DishView]:
        """Return the dishes the chef recommends, for the home page."""
        dishes = self._dish_repository.list_chefs_picks(limit)
        return [self._to_view(dish, language_code) for dish in dishes]

    def has_category(self, slug: str) -> bool:
        """Return True when a visible category has this slug."""
        category = self._category_repository.get_by_slug(slug)
        return category is not None and category.is_visible

    def is_orderable(self, dish_id: int) -> bool:
        """Return True when the dish exists, is on the menu and is in stock."""
        dish = self._dish_repository.get(dish_id)
        return dish is not None and dish.is_visible and dish.is_in_stock

    def _to_view(self, dish: Dish, language_code: str) -> DishView:
        """Copy a dish row into a view in the requested language."""
        translation = pick_translation(dish.translations, language_code)
        image = dish.images[0] if dish.images else None
        return DishView(
            id=dish.id,
            category_slug=dish.category.slug,
            name=translation.name if translation else f"#{dish.id}",
            description=translation.description if translation else "",
            ingredients=translation.ingredients if translation else "",
            serving_note=translation.serving_note if translation else "",
            price=dish.base_price,
            image_path=image.path if image else None,
            is_in_stock=dish.is_in_stock,
        )
