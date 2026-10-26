"""Queries for builders, their steps and their options."""

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from restaurant.models import Builder, BuilderOption, BuilderStep, Language
from restaurant.models.builder import BuilderOptionTranslation, BuilderStepTranslation
from restaurant.repositories.base import BaseRepository


def _with_everything(statement):  # noqa: ANN001,ANN202 - a SQLAlchemy select statement
    """Load a builder together with its names, steps, options and their texts."""
    return statement.options(
        selectinload(Builder.translations),
        selectinload(Builder.steps).selectinload(BuilderStep.translations),
        selectinload(Builder.steps)
        .selectinload(BuilderStep.options)
        .selectinload(BuilderOption.translations),
    )


class BuilderRepository(BaseRepository[Builder]):
    """Reads and removes builders, steps and options."""

    model = Builder

    def list_visible(self) -> list[Builder]:
        """Return the visible builders in menu order, complete with steps and options."""
        statement = _with_everything(
            select(Builder).where(Builder.is_visible.is_(True)).order_by(Builder.sort_order)
        )
        return list(self._session.scalars(statement.order_by(Builder.id)))

    def list_all_ordered(self) -> list[Builder]:
        """Return every builder (hidden ones too), complete with steps and options."""
        statement = _with_everything(select(Builder).order_by(Builder.sort_order, Builder.id))
        return list(self._session.scalars(statement))

    def get_by_key(self, key: str) -> Builder | None:
        """Return the builder with this key, complete, or None."""
        statement = _with_everything(select(Builder).where(Builder.key == key))
        return self._session.scalar(statement)

    def get_complete(self, builder_id: int) -> Builder | None:
        """Return the builder with this id, complete, or None."""
        statement = _with_everything(select(Builder).where(Builder.id == builder_id))
        return self._session.scalar(statement)

    def get_options(self, option_ids: list[int]) -> dict[int, BuilderOption]:
        """Return the options with these ids (any visibility), with step, builder and texts."""
        if not option_ids:
            return {}
        statement = (
            select(BuilderOption)
            .where(BuilderOption.id.in_(option_ids))
            .options(
                selectinload(BuilderOption.translations),
                selectinload(BuilderOption.step).selectinload(BuilderStep.translations),
                selectinload(BuilderOption.step).selectinload(BuilderStep.builder),
            )
        )
        return {option.id: option for option in self._session.scalars(statement)}

    def get_step(self, step_id: int) -> BuilderStep | None:
        """Return the step with this id, or None."""
        return self._session.get(BuilderStep, step_id)

    def get_option(self, option_id: int) -> BuilderOption | None:
        """Return the option with this id, or None."""
        return self._session.get(BuilderOption, option_id)

    def delete(self, entity: Builder | BuilderStep | BuilderOption) -> None:
        """Stage the removal of a builder, a step or an option. The caller commits."""
        self._session.delete(entity)

    def count_options_without_translation(self, language_code: str) -> int:
        """Return how many options have no non-empty name in this language."""
        translated = (
            select(BuilderOptionTranslation.option_id)
            .join(Language, Language.id == BuilderOptionTranslation.language_id)
            .where(Language.code == language_code, BuilderOptionTranslation.name != "")
        )
        statement = select(func.count(BuilderOption.id)).where(BuilderOption.id.not_in(translated))
        return self._session.scalar(statement) or 0

    def count_steps_without_translation(self, language_code: str) -> int:
        """Return how many steps have no non-empty title in this language."""
        translated = (
            select(BuilderStepTranslation.step_id)
            .join(Language, Language.id == BuilderStepTranslation.language_id)
            .where(Language.code == language_code, BuilderStepTranslation.title != "")
        )
        statement = select(func.count(BuilderStep.id)).where(BuilderStep.id.not_in(translated))
        return self._session.scalar(statement) or 0
