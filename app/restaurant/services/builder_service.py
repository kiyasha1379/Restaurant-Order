"""The public builders: the pages' data and the live price quote."""

from collections.abc import Sequence
from dataclasses import dataclass

from restaurant.constants import PreviewKind
from restaurant.models import Builder, BuilderOption, BuilderStep
from restaurant.repositories import BuilderRepository
from restaurant.services.build_resolver import BuildResolver, ResolvedBuild
from restaurant.services.localized import pick_translation


@dataclass(frozen=True)
class OptionView:
    """One choice in a step, in one language."""

    id: int
    key: str
    name: str
    price: int
    is_in_stock: bool
    color: str
    shape: str
    amount: int
    image_path: str | None


@dataclass(frozen=True)
class StepView:
    """One step with its visible options, in one language."""

    id: int
    key: str
    title: str
    hint: str
    is_multiple: bool
    is_required: bool
    is_base: bool
    is_layered: bool
    role: str
    options: tuple[OptionView, ...]


@dataclass(frozen=True)
class BuilderView:
    """A builder with its steps, in one language."""

    id: int
    key: str
    name: str
    hint: str
    preview_kind: PreviewKind
    steps: tuple[StepView, ...]


@dataclass(frozen=True)
class Quote:
    """The server's price for a build (one piece) and how many pieces."""

    unit_price: int
    quantity: int
    total: int
    option_names: tuple[str, ...]


class BuilderService:
    """Builds the data for the builder pages and prices a build."""

    def __init__(
        self, builder_repository: BuilderRepository, build_resolver: BuildResolver
    ) -> None:
        """Receive the repository and the build checker instead of importing them."""
        self._builders = builder_repository
        self._resolver = build_resolver

    def list_builders(self, language_code: str) -> list[BuilderView]:
        """Return the visible builders in menu order."""
        return [self._to_view(builder, language_code) for builder in self._builders.list_visible()]

    def get_builder(self, key: str, language_code: str) -> BuilderView | None:
        """Return the visible builder with this key, or None."""
        builder = self._builders.get_by_key(key)
        if builder is None or not builder.is_visible:
            return None
        return self._to_view(builder, language_code)

    def resolve(
        self, builder_key: str, option_ids: Sequence[int], language_code: str
    ) -> ResolvedBuild | None:
        """Check a build by builder key. Returns None for an unknown builder.

        Raises InvalidSelectionError when the options cannot make a build.
        """
        builder = self._builders.get_by_key(builder_key)
        if builder is None:
            return None
        return self._resolver.resolve(builder.id, option_ids, language_code)

    def quote(
        self, builder_key: str, option_ids: Sequence[int], quantity: int, language_code: str
    ) -> Quote | None:
        """Return the server's price for a build, or None for an unknown builder."""
        build = self.resolve(builder_key, option_ids, language_code)
        if build is None:
            return None
        return Quote(
            unit_price=build.unit_price,
            quantity=quantity,
            total=build.unit_price * quantity,
            option_names=tuple(option.name for option in build.options),
        )

    def _to_view(self, builder: Builder, language_code: str) -> BuilderView:
        """Copy a builder row into a view, leaving out hidden options."""
        shown = pick_translation(builder.translations, language_code)
        return BuilderView(
            id=builder.id,
            key=builder.key,
            name=shown.name if shown else builder.key,
            hint=shown.hint if shown else "",
            preview_kind=builder.preview_kind,
            steps=tuple(self._step_view(step, language_code) for step in builder.steps),
        )

    def _step_view(self, step: BuilderStep, language_code: str) -> StepView:
        """Copy a step row into a view."""
        shown = pick_translation(step.translations, language_code)
        return StepView(
            id=step.id,
            key=step.key,
            title=shown.title if shown else step.key,
            hint=shown.hint if shown else "",
            is_multiple=step.is_multiple,
            is_required=step.is_required,
            is_base=step.is_base,
            is_layered=step.is_layered,
            role=step.preview_role,
            options=tuple(
                self._option_view(option, language_code)
                for option in step.options
                if option.is_visible
            ),
        )

    @staticmethod
    def _option_view(option: BuilderOption, language_code: str) -> OptionView:
        """Copy an option row into a view."""
        shown = pick_translation(option.translations, language_code)
        return OptionView(
            id=option.id,
            key=option.key,
            name=shown.name if shown else option.key,
            price=option.price,
            is_in_stock=option.is_in_stock,
            color=option.color,
            shape=option.shape,
            amount=option.preview_amount,
            image_path=option.layer_image,
        )
