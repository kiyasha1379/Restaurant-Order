"""Admin forms for the site appearance: brand, backgrounds, home sections and home texts."""

from collections.abc import Mapping, Sequence

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import BooleanField, SelectField, StringField
from wtforms.fields import SelectChoice
from wtforms.validators import ValidationError

from restaurant.constants import DEFAULT_ACCENT_COLOR, MobileBackgroundMode
from restaurant.constants import LANGUAGE_CODE_ENGLISH as EN
from restaurant.constants import LANGUAGE_CODE_PERSIAN as FA
from restaurant.forms.fields import WholeNumberField
from restaurant.language_context import get_translator
from restaurant.services import HOME_TEXT_KEYS, BackgroundRow, SiteLook

PERCENT_RANGE = (0, 100)
HOME_TEXT_MAX_LENGTH = 400


class BrandForm(FlaskForm):
    """Brand name, accent colour and logo."""

    brand_name = StringField()
    accent_color = StringField(default=DEFAULT_ACCENT_COLOR)
    use_default_color = BooleanField()
    logo = FileField()
    remove_logo = BooleanField()

    def fill(self, look: SiteLook) -> None:
        """Show the stored look in the form."""
        self.brand_name.data = look.brand_name
        self.accent_color.data = look.accent_color or DEFAULT_ACCENT_COLOR
        self.use_default_color.data = look.accent_color is None

    def chosen_color(self) -> str | None:
        """Return the accent colour to store, or None to restore the built-in colour."""
        return None if self.use_default_color.data else (self.accent_color.data or "").strip()


class BackgroundForm(FlaskForm):
    """How one background is drawn, with optional new files."""

    dim_percent = WholeNumberField()
    is_enabled = BooleanField()
    mobile_mode = SelectField(
        choices=[SelectChoice(mode.value, mode.value) for mode in MobileBackgroundMode]
    )
    video = FileField()
    poster = FileField()
    remove_video = BooleanField()
    remove_poster = BooleanField()

    def fill(self, row: BackgroundRow) -> None:
        """Show a background's stored values in the form."""
        self.dim_percent.data = round(row.dim * 100)
        self.is_enabled.data = row.is_enabled
        self.mobile_mode.data = row.mobile_mode.value

    def validate_dim_percent(self, field: WholeNumberField) -> None:
        """Keep the dimming between 0 and 100 per cent."""
        low, high = PERCENT_RANGE
        if field.data is None or not low <= field.data <= high:
            field.data = None
            raise ValidationError(get_translator()("admin.site.error.dim"))

    def mode(self) -> MobileBackgroundMode:
        """Return the chosen mobile mode."""
        return MobileBackgroundMode(self.mobile_mode.data)


class SectionsForm(FlaskForm):
    """The order and visibility of the home sections.

    The page posts every section key as `order` (top to bottom), the checked ones as
    `visible`, and the arrow button that was pressed as `move` ("modes:up"). No script
    is needed: each arrow is a submit button.
    """

    def read(self, posted: Mapping[str, Sequence[str]]) -> tuple[list[str], set[str]]:
        """Return the new order and the visible keys, after applying the pressed arrow."""
        order = [key for key in posted.get("order", []) if key]
        visible = set(posted.get("visible", []))
        key, _, direction = (posted.get("move") or [""])[0].partition(":")
        if key in order and direction in {"up", "down"}:
            index = order.index(key)
            other = index - 1 if direction == "up" else index + 1
            if 0 <= other < len(order):
                order[index], order[other] = order[other], order[index]
        return order, visible


class HomeTextsForm(FlaskForm):
    """The editable home texts, one Persian and one English field per key."""

    def texts(self, posted: Mapping[str, str]) -> dict[str, dict[str, str]]:
        """Collect the posted texts as {key: {language: text}} (keys outside the list ignored)."""
        return {
            key: {code: posted.get(f"{key}.{code}", "")[:HOME_TEXT_MAX_LENGTH] for code in (FA, EN)}
            for key in HOME_TEXT_KEYS
        }
