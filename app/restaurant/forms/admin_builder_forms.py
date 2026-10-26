"""Admin forms for builders, steps and options. Messages follow the panel language."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import BooleanField, SelectField, StringField
from wtforms.fields import SelectChoice
from wtforms.validators import ValidationError

from restaurant.constants import LANGUAGE_CODE_ENGLISH as EN
from restaurant.constants import LANGUAGE_CODE_PERSIAN as FA
from restaurant.constants import PreviewKind
from restaurant.forms.fields import WholeNumberField
from restaurant.language_context import get_translator
from restaurant.services import BuilderInput, OptionInput, StepInput

MAX_NAME_LENGTH = 120
MAX_HINT_LENGTH = 255
MAX_PRICE = 100_000_000
MAX_SORT_ORDER = 9999
MAX_AMOUNT = 100


def _clean(field: StringField) -> str:
    """Strip the field's text in place and return it."""
    field.data = (field.data or "").strip()
    return field.data


def _require_name(field: StringField, message_key: str) -> None:
    """Require a non-empty text that is not too long."""
    if not _clean(field) or len(field.data) > MAX_NAME_LENGTH:
        raise ValidationError(get_translator()(message_key))


def _allow_short(field: StringField, longest: int) -> None:
    """Allow an empty text, but not a long one."""
    if len(_clean(field)) > longest:
        raise ValidationError(get_translator()("admin.error.too_long"))


def _small_number(field: WholeNumberField, highest: int) -> None:
    """Keep a number between 0 and `highest`; an empty field means 0."""
    field.data = field.data or 0
    if not 0 <= field.data <= highest:
        raise ValidationError(get_translator()("admin.error.number"))


class BuilderForm(FlaskForm):
    """The builder form: address key, kind of picture, order and the texts in both languages."""

    key = StringField()
    preview_kind = SelectField(
        choices=[SelectChoice(kind.value, kind.value) for kind in PreviewKind]
    )
    sort_order = WholeNumberField(default=0)
    is_visible = BooleanField(default=True)
    name_fa = StringField()
    name_en = StringField()
    hint_fa = StringField()
    hint_en = StringField()

    def validate_preview_kind(self, field: SelectField) -> None:
        """Require one of the known kinds (the default message is in English)."""
        if field.data not in {kind.value for kind in PreviewKind}:
            raise ValidationError(get_translator()("admin.error.choice"))

    def validate_sort_order(self, field: WholeNumberField) -> None:
        """Keep the order number small."""
        _small_number(field, MAX_SORT_ORDER)

    def validate_name_fa(self, field: StringField) -> None:
        """Require the Persian name."""
        _require_name(field, "admin.builders.error.name")

    def validate_name_en(self, field: StringField) -> None:
        """Allow an empty English name, but not a long one."""
        _allow_short(field, MAX_NAME_LENGTH)

    def validate_hint_fa(self, field: StringField) -> None:
        """Keep the hint short."""
        _allow_short(field, MAX_HINT_LENGTH)

    def validate_hint_en(self, field: StringField) -> None:
        """Keep the hint short."""
        _allow_short(field, MAX_HINT_LENGTH)

    def to_input(self) -> BuilderInput:
        """Return the validated values as the service's input object."""
        return BuilderInput(
            key=(self.key.data or "").strip(),
            preview_kind=PreviewKind(self.preview_kind.data),
            sort_order=self.sort_order.data,
            is_visible=self.is_visible.data,
            names={FA: self.name_fa.data, EN: self.name_en.data},
            hints={FA: self.hint_fa.data, EN: self.hint_en.data},
        )


class StepForm(FlaskForm):
    """The step form: key, switches, the role in the picture and the texts."""

    key = StringField()
    sort_order = WholeNumberField(default=0)
    is_multiple = BooleanField()
    is_required = BooleanField(default=True)
    is_base = BooleanField()
    is_layered = BooleanField()
    preview_role = SelectField()
    title_fa = StringField()
    title_en = StringField()
    hint_fa = StringField()
    hint_en = StringField()

    def set_role_choices(self, choices: list[tuple[str, str]]) -> None:
        """Fill the picture-role list with (value, label) pairs."""
        self.preview_role.choices = [SelectChoice(value, label) for value, label in choices]

    def validate_preview_role(self, field: SelectField) -> None:
        """Require one of the roles that fit the builder's picture."""
        if field.data not in {choice.value for choice in field.choices}:
            raise ValidationError(get_translator()("admin.error.choice"))

    def validate_sort_order(self, field: WholeNumberField) -> None:
        """Keep the order number small."""
        _small_number(field, MAX_SORT_ORDER)

    def validate_title_fa(self, field: StringField) -> None:
        """Require the Persian title."""
        _require_name(field, "admin.builders.error.name")

    def validate_title_en(self, field: StringField) -> None:
        """Allow an empty English title, but not a long one."""
        _allow_short(field, MAX_NAME_LENGTH)

    def validate_hint_fa(self, field: StringField) -> None:
        """Keep the hint short."""
        _allow_short(field, MAX_HINT_LENGTH)

    def validate_hint_en(self, field: StringField) -> None:
        """Keep the hint short."""
        _allow_short(field, MAX_HINT_LENGTH)

    def to_input(self) -> StepInput:
        """Return the validated values as the service's input object."""
        return StepInput(
            key=(self.key.data or "").strip(),
            sort_order=self.sort_order.data,
            is_multiple=self.is_multiple.data,
            is_required=self.is_required.data,
            is_base=self.is_base.data,
            is_layered=self.is_layered.data,
            preview_role=self.preview_role.data or "",
            titles={FA: self.title_fa.data, EN: self.title_en.data},
            hints={FA: self.hint_fa.data, EN: self.hint_en.data},
        )


class OptionForm(FlaskForm):
    """The option form: key, price, switches, how it looks in the picture, names and a photo."""

    key = StringField()
    price = WholeNumberField(default=0)
    sort_order = WholeNumberField(default=0)
    is_in_stock = BooleanField(default=True)
    is_visible = BooleanField(default=True)
    color = StringField()
    shape = StringField()
    preview_amount = WholeNumberField(default=0)
    name_fa = StringField()
    name_en = StringField()
    photo = FileField()
    remove_photo = BooleanField()

    def validate_price(self, field: WholeNumberField) -> None:
        """Require a price between 0 and the maximum; an empty field means free."""
        field.data = field.data or 0
        if not 0 <= field.data <= MAX_PRICE:
            raise ValidationError(get_translator()("admin.menu.error.price"))

    def validate_sort_order(self, field: WholeNumberField) -> None:
        """Keep the order number small."""
        _small_number(field, MAX_SORT_ORDER)

    def validate_preview_amount(self, field: WholeNumberField) -> None:
        """Keep the picture size between 0 and 100."""
        _small_number(field, MAX_AMOUNT)

    def validate_name_fa(self, field: StringField) -> None:
        """Require the Persian name."""
        _require_name(field, "admin.builders.error.name")

    def validate_name_en(self, field: StringField) -> None:
        """Allow an empty English name, but not a long one."""
        _allow_short(field, MAX_NAME_LENGTH)

    def to_input(self) -> OptionInput:
        """Return the validated values as the service's input object."""
        return OptionInput(
            key=(self.key.data or "").strip(),
            price=self.price.data,
            sort_order=self.sort_order.data,
            is_in_stock=self.is_in_stock.data,
            is_visible=self.is_visible.data,
            color=(self.color.data or "").strip(),
            shape=(self.shape.data or "").strip(),
            preview_amount=self.preview_amount.data,
            names={FA: self.name_fa.data, EN: self.name_en.data},
        )
