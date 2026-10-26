"""Changing builders from the admin panel: builders, steps, options, photos and their order."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from restaurant.constants import PREVIEW_ROLES_BY_KIND, PreviewKind, PreviewRole
from restaurant.models import (
    Builder,
    BuilderOption,
    BuilderOptionTranslation,
    BuilderStep,
    BuilderStepTranslation,
    BuilderTranslation,
)
from restaurant.repositories import BuilderRepository, LanguageRepository

KEY_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COLOR_PATTERN = re.compile(r"^(#[0-9a-fA-F]{6})?$")
SHAPE_PATTERN = re.compile(r"^[a-z-]{0,20}$")
MAX_KEY_LENGTH = 40
MOVE_UP = -1
MOVE_DOWN = 1


class BuilderAdminError(ValueError):
    """A builder change was refused."""


class InvalidKeyError(BuilderAdminError):
    """The key is empty, too long or has characters other than a-z, 0-9 and dashes."""


class DuplicateKeyError(BuilderAdminError):
    """Another row in the same place already uses this key."""


class InvalidPreviewRoleError(BuilderAdminError):
    """The step's picture role does not fit the builder's kind of picture."""


class InvalidAppearanceError(BuilderAdminError):
    """The colour or the shape of an option has a form the picture cannot draw."""


@dataclass(frozen=True)
class BuilderInput:
    """Everything the builder form collects. `names` and `hints` are keyed by language code."""

    key: str
    preview_kind: PreviewKind
    sort_order: int = 0
    is_visible: bool = True
    names: Mapping[str, str] = field(default_factory=dict)
    hints: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class StepInput:
    """Everything the step form collects. `titles` and `hints` are keyed by language code."""

    key: str
    sort_order: int = 0
    is_multiple: bool = False
    is_required: bool = True
    is_base: bool = False
    is_layered: bool = False
    preview_role: str = ""
    titles: Mapping[str, str] = field(default_factory=dict)
    hints: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class OptionInput:
    """Everything the option form collects. `names` is keyed by language code."""

    key: str
    price: int
    sort_order: int = 0
    is_in_stock: bool = True
    is_visible: bool = True
    color: str = ""
    shape: str = ""
    preview_amount: int = 0
    names: Mapping[str, str] = field(default_factory=dict)


class BuilderAdminService:
    """Creates, changes and removes builder rows. The caller commits."""

    def __init__(
        self, builder_repository: BuilderRepository, language_repository: LanguageRepository
    ) -> None:
        """Receive the repositories instead of importing them, so tests can swap them."""
        self._builders = builder_repository
        self._languages = language_repository

    # --- reading -------------------------------------------------------

    def list_builders(self) -> list[Builder]:
        """Return every builder (hidden ones too), complete."""
        return self._builders.list_all_ordered()

    def get_builder(self, builder_id: int) -> Builder | None:
        """Return the builder with this id, or None."""
        return self._builders.get_complete(builder_id)

    def get_step(self, step_id: int) -> BuilderStep | None:
        """Return the step with this id, or None."""
        return self._builders.get_step(step_id)

    def get_option(self, option_id: int) -> BuilderOption | None:
        """Return the option with this id, or None."""
        return self._builders.get_option(option_id)

    @staticmethod
    def roles_for(kind: PreviewKind) -> tuple[PreviewRole, ...]:
        """Return the picture roles a step may have in this kind of builder."""
        return PREVIEW_ROLES_BY_KIND[kind]

    # --- builders ------------------------------------------------------

    def create_builder(self, data: BuilderInput) -> Builder:
        """Add a builder. Raises InvalidKeyError or DuplicateKeyError."""
        builder = Builder()
        self._apply_builder(builder, data)
        return self._builders.add(builder)

    def update_builder(self, builder: Builder, data: BuilderInput) -> Builder:
        """Change a builder. Steps whose role no longer fits the new picture lose their role."""
        self._apply_builder(builder, data)
        allowed = {role.value for role in PREVIEW_ROLES_BY_KIND[builder.preview_kind]}
        for step in builder.steps:
            if step.preview_role not in allowed:
                step.preview_role = ""
        return builder

    def delete_builder(self, builder: Builder) -> list[str]:
        """Remove a builder; return its option photo paths so the caller can delete the files."""
        paths = [
            option.layer_image
            for step in builder.steps
            for option in step.options
            if option.layer_image
        ]
        self._builders.delete(builder)
        return paths

    def move_builder(self, builder: Builder, direction: int) -> None:
        """Move a builder one place earlier (-1) or later (+1)."""
        self._move_within(self._builders.list_all_ordered(), builder, direction)

    # --- steps ---------------------------------------------------------

    def create_step(self, builder: Builder, data: StepInput) -> BuilderStep:
        """Add a step at the end of a builder. Raises InvalidKeyError, DuplicateKeyError, ..."""
        step = BuilderStep()
        self._apply_step(builder, step, data)
        builder.steps.append(step)
        return step

    def update_step(self, step: BuilderStep, data: StepInput) -> BuilderStep:
        """Change a step. Raises InvalidKeyError, DuplicateKeyError or InvalidPreviewRoleError."""
        self._apply_step(step.builder, step, data)
        return step

    def delete_step(self, step: BuilderStep) -> list[str]:
        """Remove a step; return its option photo paths so the caller can delete the files."""
        paths = [option.layer_image for option in step.options if option.layer_image]
        self._builders.delete(step)
        return paths

    def move_step(self, step: BuilderStep, direction: int) -> None:
        """Move a step one place earlier (-1) or later (+1) inside its builder."""
        self._move_within(list(step.builder.steps), step, direction)

    # --- options -------------------------------------------------------

    def create_option(self, step: BuilderStep, data: OptionInput) -> BuilderOption:
        """Add an option to a step. Raises InvalidKeyError, DuplicateKeyError, ..."""
        option = BuilderOption()
        self._apply_option(step, option, data)
        step.options.append(option)
        return option

    def update_option(self, option: BuilderOption, data: OptionInput) -> BuilderOption:
        """Change an option. Raises InvalidKeyError, DuplicateKeyError or InvalidAppearanceError."""
        self._apply_option(option.step, option, data)
        return option

    def delete_option(self, option: BuilderOption) -> str | None:
        """Remove an option; return its photo path (to delete), if it had one."""
        path = option.layer_image
        self._builders.delete(option)
        return path

    @staticmethod
    def set_option_in_stock(option: BuilderOption, in_stock: bool) -> None:
        """Mark an option as available or sold out."""
        option.is_in_stock = in_stock

    @staticmethod
    def set_option_visible(option: BuilderOption, visible: bool) -> None:
        """Show or hide an option on the public page."""
        option.is_visible = visible

    @staticmethod
    def set_option_image(option: BuilderOption, path: str) -> str | None:
        """Make `path` the option's picture; return the old path (to delete), if any."""
        old_path, option.layer_image = option.layer_image, path
        return old_path

    @staticmethod
    def remove_option_image(option: BuilderOption) -> str | None:
        """Remove the option's picture; return its path (to delete), if there was one."""
        old_path, option.layer_image = option.layer_image, None
        return old_path

    def move_option(self, option: BuilderOption, direction: int) -> None:
        """Move an option one place earlier (-1) or later (+1) inside its step."""
        self._move_within(list(option.step.options), option, direction)

    # --- helpers -------------------------------------------------------

    @staticmethod
    def _clean_key(key: str) -> str:
        """Return the key trimmed and lowercased, or raise InvalidKeyError."""
        cleaned = (key or "").strip().lower()
        if not cleaned or len(cleaned) > MAX_KEY_LENGTH or not KEY_PATTERN.match(cleaned):
            raise InvalidKeyError(cleaned)
        return cleaned

    def _apply_builder(self, builder: Builder, data: BuilderInput) -> None:
        """Copy the form values onto the builder and its text rows."""
        key = self._clean_key(data.key)
        other = self._builders.get_by_key(key)
        if other is not None and other is not builder:
            raise DuplicateKeyError(key)
        builder.key = key
        builder.preview_kind = data.preview_kind
        builder.sort_order = data.sort_order
        builder.is_visible = data.is_visible
        self._apply_texts(
            builder.translations,
            BuilderTranslation,
            {
                code: {"name": data.names.get(code, ""), "hint": data.hints.get(code, "")}
                for code in set(data.names) | set(data.hints)
            },
            required="name",
        )

    def _apply_step(self, builder: Builder, step: BuilderStep, data: StepInput) -> None:
        """Copy the form values onto the step and its text rows."""
        key = self._clean_key(data.key)
        if any(other.key == key and other is not step for other in builder.steps):
            raise DuplicateKeyError(key)
        allowed_roles = {role.value for role in PREVIEW_ROLES_BY_KIND[builder.preview_kind]}
        if data.preview_role not in allowed_roles:
            raise InvalidPreviewRoleError(data.preview_role)
        step.key = key
        step.sort_order = data.sort_order
        step.is_layered = data.is_layered
        # Reordering only makes sense when several options can be chosen.
        step.is_multiple = data.is_multiple or data.is_layered
        step.is_required = data.is_required
        step.is_base = data.is_base
        step.preview_role = data.preview_role
        self._apply_texts(
            step.translations,
            BuilderStepTranslation,
            {
                code: {"title": data.titles.get(code, ""), "hint": data.hints.get(code, "")}
                for code in set(data.titles) | set(data.hints)
            },
            required="title",
        )

    def _apply_option(self, step: BuilderStep, option: BuilderOption, data: OptionInput) -> None:
        """Copy the form values onto the option and its name rows."""
        key = self._clean_key(data.key)
        if any(other.key == key and other is not option for other in step.options):
            raise DuplicateKeyError(key)
        color = (data.color or "").strip()
        shape = (data.shape or "").strip().lower()
        if not COLOR_PATTERN.match(color) or not SHAPE_PATTERN.match(shape):
            raise InvalidAppearanceError(f"{color} {shape}")
        option.key = key
        option.price = data.price
        option.sort_order = data.sort_order
        option.is_in_stock = data.is_in_stock
        option.is_visible = data.is_visible
        option.color = color
        option.shape = shape
        option.preview_amount = data.preview_amount
        self._apply_texts(
            option.translations,
            BuilderOptionTranslation,
            {code: {"name": name} for code, name in data.names.items()},
            required="name",
        )

    def _apply_texts(
        self,
        rows: list,
        row_type: type,
        values: Mapping[str, Mapping[str, str]],
        required: str,
    ) -> None:
        """Create, change or remove the translation rows; a row without its main text is removed."""
        existing = {row.language.code: row for row in rows}
        for code, fields in values.items():
            row = existing.get(code)
            main = (fields.get(required) or "").strip()
            if not main:
                if row is not None:
                    rows.remove(row)
                continue
            if row is None:
                row = row_type(language_id=self._language_id(code))
                rows.append(row)
            for name, text in fields.items():
                setattr(row, name, (text or "").strip())

    def _language_id(self, code: str) -> int:
        """Return the id of the language with this code."""
        language = self._languages.get_by_code(code)
        if language is None:
            raise BuilderAdminError(f"Unknown language {code}")
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
