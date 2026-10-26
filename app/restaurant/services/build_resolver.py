"""Checks a customer's choices for a builder and works out their price.

This is the only place that decides whether a build is valid and what it costs;
the browser's live price is only a preview (technical plan, section 7).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from restaurant.models import Builder, BuilderOption
from restaurant.repositories import BuilderRepository
from restaurant.services.localized import exact_translation, pick_translation

MAX_OPTIONS_PER_BUILD = 40


class SelectionProblem(StrEnum):
    """Why a build was refused; each value is part of the text key `builder.error.<value>`."""

    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"
    TOO_MANY = "too_many"
    MISSING = "missing"


class InvalidSelectionError(ValueError):
    """The chosen options cannot make a build; `problem` says why."""

    def __init__(self, problem: SelectionProblem) -> None:
        """Keep the reason so the caller can answer in the page language."""
        super().__init__(problem.value)
        self.problem = problem


@dataclass(frozen=True)
class PricedOption:
    """One chosen option with its names (both languages) and price, in build order."""

    option_id: int
    name: str
    name_fa: str
    name_en: str
    group: str
    group_fa: str
    group_en: str
    price: int
    order_index: int


@dataclass(frozen=True)
class ResolvedBuild:
    """A valid build: its builder names, the options in order and the price of one."""

    builder_id: int
    name: str
    name_fa: str
    name_en: str
    options: tuple[PricedOption, ...]
    unit_price: int

    @property
    def option_ids(self) -> tuple[int, ...]:
        """Return the chosen option ids in build order."""
        return tuple(option.option_id for option in self.options)


class BuildResolver:
    """Validates a list of option ids against a builder and prices it."""

    def __init__(self, builder_repository: BuilderRepository) -> None:
        """Receive the repository instead of importing it, so tests can swap it."""
        self._builders = builder_repository

    def resolve(
        self, builder_id: int, option_ids: Sequence[int], language_code: str
    ) -> ResolvedBuild:
        """Return the build for these options. Raises InvalidSelectionError when it is not valid.

        Options of a layered step keep the order the customer gave; every other option
        follows the order of the steps. The result lists them in that build order.
        """
        builder = self._builders.get_complete(builder_id)
        if builder is None or not builder.is_visible:
            raise InvalidSelectionError(SelectionProblem.UNKNOWN)
        chosen = self._load_chosen(builder, option_ids)
        self._check_steps(builder, chosen)
        ordered = self._in_build_order(builder, chosen)
        priced = tuple(
            self._price_option(option, index, language_code) for index, option in enumerate(ordered)
        )
        names = self._builder_names(builder, language_code)
        return ResolvedBuild(
            builder_id=builder.id,
            name=names[0],
            name_fa=names[1],
            name_en=names[2],
            options=priced,
            unit_price=sum(option.price for option in priced),
        )

    def _load_chosen(self, builder: Builder, option_ids: Sequence[int]) -> list[BuilderOption]:
        """Return the chosen options in the given order; refuse unknown, hidden or sold-out ones."""
        ids = list(option_ids)
        if not ids or len(ids) > MAX_OPTIONS_PER_BUILD or len(set(ids)) != len(ids):
            raise InvalidSelectionError(
                SelectionProblem.MISSING if not ids else SelectionProblem.UNKNOWN
            )
        found = self._builders.get_options(ids)
        chosen = []
        for option_id in ids:
            option = found.get(option_id)
            if option is None or option.step.builder_id != builder.id:
                raise InvalidSelectionError(SelectionProblem.UNKNOWN)
            if not option.is_visible or not option.is_in_stock:
                raise InvalidSelectionError(SelectionProblem.UNAVAILABLE)
            chosen.append(option)
        return chosen

    @staticmethod
    def _check_steps(builder: Builder, chosen: list[BuilderOption]) -> None:
        """Enforce 'one choice only' and 'required' for every step."""
        per_step: dict[int, int] = {}
        for option in chosen:
            per_step[option.step_id] = per_step.get(option.step_id, 0) + 1
        for step in builder.steps:
            picked = per_step.get(step.id, 0)
            if picked > 1 and not step.is_multiple:
                raise InvalidSelectionError(SelectionProblem.TOO_MANY)
            # A required step with nothing left to pick (all sold out) cannot block the order.
            orderable = any(o.is_visible and o.is_in_stock for o in step.options)
            if picked == 0 and step.is_required and orderable:
                raise InvalidSelectionError(SelectionProblem.MISSING)

    @staticmethod
    def _in_build_order(builder: Builder, chosen: list[BuilderOption]) -> list[BuilderOption]:
        """Put the options of ordinary steps first (step order), then the layers as given."""
        step_position = {step.id: index for index, step in enumerate(builder.steps)}
        plain = [option for option in chosen if not option.step.is_layered]
        layers = [option for option in chosen if option.step.is_layered]
        option_position = {
            option.id: index for step in builder.steps for index, option in enumerate(step.options)
        }
        plain.sort(key=lambda option: (step_position[option.step_id], option_position[option.id]))
        return plain + layers

    @staticmethod
    def _price_option(option: BuilderOption, index: int, language_code: str) -> PricedOption:
        """Copy an option's names (both languages) and price for the order."""
        shown = pick_translation(option.translations, language_code)
        persian = exact_translation(option.translations, "fa") or shown
        english = exact_translation(option.translations, "en")
        step_shown = pick_translation(option.step.translations, language_code)
        step_persian = exact_translation(option.step.translations, "fa") or step_shown
        step_english = exact_translation(option.step.translations, "en")
        return PricedOption(
            option_id=option.id,
            name=shown.name if shown else option.key,
            name_fa=persian.name if persian else option.key,
            name_en=english.name if english else "",
            group=step_shown.title if step_shown else option.step.key,
            group_fa=step_persian.title if step_persian else option.step.key,
            group_en=step_english.title if step_english else "",
            price=option.price,
            order_index=index,
        )

    @staticmethod
    def _builder_names(builder: Builder, language_code: str) -> tuple[str, str, str]:
        """Return the builder's name in the page language, in Persian and in English."""
        shown = pick_translation(builder.translations, language_code)
        persian = exact_translation(builder.translations, "fa") or shown
        english = exact_translation(builder.translations, "en")
        return (
            shown.name if shown else builder.key,
            persian.name if persian else builder.key,
            english.name if english else "",
        )
