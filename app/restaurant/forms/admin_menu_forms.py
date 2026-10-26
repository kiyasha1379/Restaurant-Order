"""Admin forms for dishes and categories. Messages follow the panel language."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import BooleanField, SelectField, StringField, TextAreaField
from wtforms.validators import ValidationError

from restaurant.constants import LANGUAGE_CODE_ENGLISH as EN
from restaurant.constants import LANGUAGE_CODE_PERSIAN as FA
from restaurant.forms.fields import WholeNumberField
from restaurant.language_context import get_translator
from restaurant.services import CategoryInput, DishInput, DishTexts

MAX_NAME_LENGTH = 120
MAX_DESCRIPTION_LENGTH = 1000
MAX_INGREDIENTS_LENGTH = 500
MAX_SERVING_NOTE_LENGTH = 120
MAX_PRICE = 100_000_000
MAX_SORT_ORDER = 9999


def _clean(field: StringField) -> str:
    """Strip the field's text in place and return it."""
    field.data = (field.data or "").strip()
    return field.data


def _require_within(field: StringField, longest: int, message_key: str) -> None:
    """Raise a translated error when the text is longer than `longest`."""
    if len(_clean(field)) > longest:
        raise ValidationError(get_translator()(message_key))


class DishForm(FlaskForm):
    """The dish form: numbers, switches, texts in both languages and an optional photo."""

    category_id = SelectField(coerce=int)
    base_price = WholeNumberField()
    sort_order = WholeNumberField(default=0)
    is_in_stock = BooleanField(default=True)
    is_chefs_pick = BooleanField()
    is_visible = BooleanField(default=True)
    name_fa = StringField()
    name_en = StringField()
    description_fa = TextAreaField()
    description_en = TextAreaField()
    ingredients_fa = TextAreaField()
    ingredients_en = TextAreaField()
    serving_note_fa = StringField()
    serving_note_en = StringField()
    photo = FileField()
    remove_photo = BooleanField()

    def set_category_choices(self, categories: list[tuple[int, str]]) -> None:
        """Fill the category list with (id, name) pairs."""
        self.category_id.choices = categories

    def validate_category_id(self, field: SelectField) -> None:
        """Require one of the listed categories (the default 'not valid choice' is in English)."""
        if field.data not in {value for value, _ in field.choices}:
            raise ValidationError(get_translator()("admin.error.choice"))

    def validate_base_price(self, field: WholeNumberField) -> None:
        """Require a price between 0 and the maximum."""
        if field.data is None or not 0 <= field.data <= MAX_PRICE:
            raise ValidationError(get_translator()("admin.menu.error.price"))

    def validate_sort_order(self, field: WholeNumberField) -> None:
        """Keep the order number small; an empty field means 0."""
        field.data = field.data or 0
        if not 0 <= field.data <= MAX_SORT_ORDER:
            raise ValidationError(get_translator()("admin.error.number"))

    def validate_name_fa(self, field: StringField) -> None:
        """Require the Persian name: Persian is the language every other falls back to."""
        if not _clean(field) or len(field.data) > MAX_NAME_LENGTH:
            raise ValidationError(get_translator()("admin.menu.error.name"))

    def validate_name_en(self, field: StringField) -> None:
        """Allow an empty English name, but not a long one."""
        _require_within(field, MAX_NAME_LENGTH, "admin.menu.error.name")

    def validate_description_fa(self, field: TextAreaField) -> None:
        """Keep the description short."""
        _require_within(field, MAX_DESCRIPTION_LENGTH, "admin.error.too_long")

    def validate_description_en(self, field: TextAreaField) -> None:
        """Keep the description short."""
        _require_within(field, MAX_DESCRIPTION_LENGTH, "admin.error.too_long")

    def validate_ingredients_fa(self, field: TextAreaField) -> None:
        """Keep the ingredients short."""
        _require_within(field, MAX_INGREDIENTS_LENGTH, "admin.error.too_long")

    def validate_ingredients_en(self, field: TextAreaField) -> None:
        """Keep the ingredients short."""
        _require_within(field, MAX_INGREDIENTS_LENGTH, "admin.error.too_long")

    def validate_serving_note_fa(self, field: StringField) -> None:
        """Keep the serving note short."""
        _require_within(field, MAX_SERVING_NOTE_LENGTH, "admin.error.too_long")

    def validate_serving_note_en(self, field: StringField) -> None:
        """Keep the serving note short."""
        _require_within(field, MAX_SERVING_NOTE_LENGTH, "admin.error.too_long")

    def to_input(self) -> DishInput:
        """Return the validated values as the service's input object."""
        texts = {
            code: DishTexts(
                name=getattr(self, f"name_{code}").data,
                description=getattr(self, f"description_{code}").data,
                ingredients=getattr(self, f"ingredients_{code}").data,
                serving_note=getattr(self, f"serving_note_{code}").data,
            )
            for code in (FA, EN)
        }
        return DishInput(
            category_id=self.category_id.data,
            base_price=self.base_price.data,
            sort_order=self.sort_order.data,
            is_in_stock=self.is_in_stock.data,
            is_chefs_pick=self.is_chefs_pick.data,
            is_visible=self.is_visible.data,
            texts=texts,
        )


class CategoryForm(FlaskForm):
    """The category form: a slug (the address part), the order and the two names."""

    slug = StringField()
    sort_order = WholeNumberField(default=0)
    is_visible = BooleanField(default=True)
    name_fa = StringField()
    name_en = StringField()

    def validate_sort_order(self, field: WholeNumberField) -> None:
        """Keep the order number small; an empty field means 0."""
        field.data = field.data or 0
        if not 0 <= field.data <= MAX_SORT_ORDER:
            raise ValidationError(get_translator()("admin.error.number"))

    def validate_name_fa(self, field: StringField) -> None:
        """Require the Persian name."""
        if not _clean(field) or len(field.data) > MAX_NAME_LENGTH:
            raise ValidationError(get_translator()("admin.menu.error.name"))

    def validate_name_en(self, field: StringField) -> None:
        """Allow an empty English name, but not a long one."""
        _require_within(field, MAX_NAME_LENGTH, "admin.menu.error.name")

    def to_input(self) -> CategoryInput:
        """Return the validated values as the service's input object."""
        return CategoryInput(
            slug=(self.slug.data or "").strip(),
            sort_order=self.sort_order.data,
            is_visible=self.is_visible.data,
            names={FA: self.name_fa.data, EN: self.name_en.data},
        )
