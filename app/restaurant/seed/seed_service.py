"""Fills an empty database with the demo's sample content. Safe to run twice."""

from dataclasses import dataclass

from restaurant.constants import LANGUAGE_CODE_ENGLISH, LANGUAGE_CODE_PERSIAN
from restaurant.models import (
    Background,
    Builder,
    BuilderOption,
    BuilderOptionTranslation,
    BuilderStep,
    BuilderStepTranslation,
    BuilderTranslation,
    Category,
    CategoryTranslation,
    Dish,
    DishTranslation,
)
from restaurant.repositories import (
    BackgroundRepository,
    BuilderRepository,
    CategoryRepository,
    DishRepository,
    LanguageRepository,
)
from restaurant.seed.demo_builders import DEMO_BUILDERS, DemoBuilder, DemoOption, DemoStep
from restaurant.seed.demo_data import DEMO_BACKGROUNDS, DEMO_CATEGORIES, DemoCategory, DemoDish


@dataclass(frozen=True)
class SeedReport:
    """How many rows one seed run added."""

    backgrounds: int = 0
    categories: int = 0
    dishes: int = 0
    builders: int = 0


class DemoSeedService:
    """Adds sample backgrounds, categories and dishes that are not there yet."""

    def __init__(
        self,
        language_repository: LanguageRepository,
        background_repository: BackgroundRepository,
        category_repository: CategoryRepository,
        dish_repository: DishRepository,
        builder_repository: BuilderRepository,
    ) -> None:
        """Receive the repositories instead of importing them, so tests can swap them."""
        self._language_repository = language_repository
        self._background_repository = background_repository
        self._category_repository = category_repository
        self._dish_repository = dish_repository
        self._builder_repository = builder_repository

    def seed(self) -> SeedReport:
        """Add whatever is missing. Existing rows are never changed. The caller commits."""
        backgrounds = self._seed_backgrounds()
        categories, dishes = self._seed_menu()
        builders = self._seed_builders()
        return SeedReport(
            backgrounds=backgrounds, categories=categories, dishes=dishes, builders=builders
        )

    def _seed_backgrounds(self) -> int:
        """Add the backgrounds whose key is not in the table yet."""
        added = 0
        for demo in DEMO_BACKGROUNDS:
            if self._background_repository.get_by_key(demo.key) is not None:
                continue
            self._background_repository.add(
                Background(
                    key=demo.key,
                    video_path=demo.video_path,
                    poster_path=demo.poster_path,
                    dim=demo.dim,
                    mobile_mode=demo.mobile_mode,
                )
            )
            added += 1
        return added

    def _seed_menu(self) -> tuple[int, int]:
        """Add categories that are missing, with their dishes. Returns (categories, dishes)."""
        language_ids = self._language_ids()
        categories_added = dishes_added = 0
        for sort_order, demo_category in enumerate(DEMO_CATEGORIES):
            if self._category_repository.get_by_slug(demo_category.slug) is not None:
                continue
            category = self._build_category(demo_category, sort_order, language_ids)
            self._category_repository.add(category)
            categories_added += 1
            for dish_order, demo_dish in enumerate(demo_category.dishes):
                self._dish_repository.add(
                    self._build_dish(demo_dish, category, dish_order, language_ids)
                )
                dishes_added += 1
        return categories_added, dishes_added

    def _seed_builders(self) -> int:
        """Add the builders whose key is not in the table yet. Returns how many were added."""
        language_ids = self._language_ids()
        added = 0
        for sort_order, demo in enumerate(DEMO_BUILDERS):
            if self._builder_repository.get_by_key(demo.key) is not None:
                continue
            self._builder_repository.add(self._build_builder(demo, sort_order, language_ids))
            added += 1
        return added

    @staticmethod
    def _texts(
        language_ids: dict[str, int], pair: tuple[str, str], factory
    ) -> list:  # noqa: ANN001
        """Make one translation row per language from a (Persian, English) pair."""
        return [
            factory(language_ids[code], pair[index])
            for index, code in enumerate((LANGUAGE_CODE_PERSIAN, LANGUAGE_CODE_ENGLISH))
        ]

    def _build_builder(
        self, demo: DemoBuilder, sort_order: int, language_ids: dict[str, int]
    ) -> Builder:
        """Create a builder row with its steps and options."""
        names = self._texts(
            language_ids,
            (demo.name[0], demo.name[1]),
            lambda language_id, name: BuilderTranslation(language_id=language_id, name=name),
        )
        for translation, hint in zip(names, demo.hint, strict=True):
            translation.hint = hint
        return Builder(
            key=demo.key,
            preview_kind=demo.kind,
            sort_order=sort_order,
            translations=names,
            steps=[
                self._build_step(step, index, language_ids) for index, step in enumerate(demo.steps)
            ],
        )

    def _build_step(
        self, demo: DemoStep, sort_order: int, language_ids: dict[str, int]
    ) -> BuilderStep:
        """Create a step row with its options."""
        return BuilderStep(
            key=demo.key,
            sort_order=sort_order,
            is_multiple=demo.is_multiple,
            is_required=demo.is_required,
            is_base=demo.is_base,
            is_layered=demo.is_layered,
            preview_role=demo.role.value,
            translations=self._texts(
                language_ids,
                demo.title,
                lambda language_id, title: BuilderStepTranslation(
                    language_id=language_id, title=title
                ),
            ),
            options=[
                self._build_option(option, index, language_ids)
                for index, option in enumerate(demo.options)
            ],
        )

    def _build_option(
        self, demo: DemoOption, sort_order: int, language_ids: dict[str, int]
    ) -> BuilderOption:
        """Create an option row with its two names."""
        return BuilderOption(
            key=demo.key,
            price=demo.price,
            sort_order=sort_order,
            color=demo.color,
            shape=demo.shape,
            preview_amount=demo.amount,
            translations=self._texts(
                language_ids,
                demo.name,
                lambda language_id, name: BuilderOptionTranslation(
                    language_id=language_id, name=name
                ),
            ),
        )

    def _language_ids(self) -> dict[str, int]:
        """Return the ids of the Persian and English rows, which the migration creates."""
        ids = {}
        for code in (LANGUAGE_CODE_PERSIAN, LANGUAGE_CODE_ENGLISH):
            language = self._language_repository.get_by_code(code)
            if language is None:
                raise RuntimeError(f"Language '{code}' is missing; run `flask db upgrade` first.")
            ids[code] = language.id
        return ids

    @staticmethod
    def _build_category(
        demo: DemoCategory, sort_order: int, language_ids: dict[str, int]
    ) -> Category:
        """Create a category row with its two names."""
        fa_name, en_name = demo.name
        return Category(
            slug=demo.slug,
            sort_order=sort_order,
            translations=[
                CategoryTranslation(language_id=language_ids[LANGUAGE_CODE_PERSIAN], name=fa_name),
                CategoryTranslation(language_id=language_ids[LANGUAGE_CODE_ENGLISH], name=en_name),
            ],
        )

    @staticmethod
    def _build_dish(
        demo: DemoDish, category: Category, sort_order: int, language_ids: dict[str, int]
    ) -> Dish:
        """Create a dish row with its two translations."""
        translations = [
            DishTranslation(
                language_id=language_ids[code],
                name=demo.name[index],
                description=demo.description[index],
                ingredients=demo.ingredients[index],
                serving_note=demo.serving_note[index],
            )
            for index, code in enumerate((LANGUAGE_CODE_PERSIAN, LANGUAGE_CODE_ENGLISH))
        ]
        return Dish(
            category=category,
            base_price=demo.price,
            is_chefs_pick=demo.is_chefs_pick,
            sort_order=sort_order,
            translations=translations,
        )
