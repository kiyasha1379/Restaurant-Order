"""Admin forms for staff accounts and roles. Messages follow the panel language."""

import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectMultipleField, StringField
from wtforms.validators import ValidationError
from wtforms.widgets import CheckboxInput, ListWidget

from restaurant.constants import MIN_PASSWORD_LENGTH
from restaurant.language_context import get_translator

MAX_EMAIL_LENGTH = 255
MAX_NAME_LENGTH = 120
MAX_ROLE_NAME_LENGTH = 80
MAX_PASSWORD_LENGTH = 200
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clean(field: StringField) -> str:
    """Strip the field's text in place and return it."""
    field.data = (field.data or "").strip()
    return field.data


class StaffForm(FlaskForm):
    """A staff account: e-mail (set once), name, roles, password and the blocked switch."""

    email = StringField()
    display_name = StringField()
    password = PasswordField()
    role_ids = SelectMultipleField(
        coerce=int, widget=ListWidget(prefix_label=False), option_widget=CheckboxInput()
    )
    is_active = BooleanField(default=True)

    def __init__(self, *args, is_new: bool, **kwargs) -> None:
        """Remember whether the account is new: only then e-mail and password are required."""
        super().__init__(*args, **kwargs)
        self.is_new = is_new

    def set_role_choices(self, roles: list[tuple[int, str]]) -> None:
        """Fill the role list with (id, name) pairs."""
        self.role_ids.choices = roles

    def validate_email(self, field: StringField) -> None:
        """Require a plausible address when creating; an existing account keeps its own."""
        if not self.is_new:
            return
        value = _clean(field).lower()
        field.data = value
        if not EMAIL_PATTERN.match(value) or len(value) > MAX_EMAIL_LENGTH:
            raise ValidationError(get_translator()("admin.users.error.email"))

    def validate_display_name(self, field: StringField) -> None:
        """Require a name that fits the column."""
        if not _clean(field) or len(field.data) > MAX_NAME_LENGTH:
            raise ValidationError(get_translator()("admin.users.error.name"))

    def validate_password(self, field: PasswordField) -> None:
        """Require a long enough password; when editing, an empty one keeps the old password."""
        value = field.data or ""
        if not value and not self.is_new:
            return
        if len(value) < MIN_PASSWORD_LENGTH or len(value) > MAX_PASSWORD_LENGTH:
            raise ValidationError(get_translator()("admin.users.error.password"))

    def validate_role_ids(self, field: SelectMultipleField) -> None:
        """Require at least one role: an account without a role is not staff any more."""
        if not field.data:
            raise ValidationError(get_translator()("admin.users.error.roles"))


class RoleForm(FlaskForm):
    """The two names of a role. The permission matrix is read from the request separately."""

    name_fa = StringField()
    name_en = StringField()

    def validate_name_fa(self, field: StringField) -> None:
        """Require the Persian name."""
        if not _clean(field) or len(field.data) > MAX_ROLE_NAME_LENGTH:
            raise ValidationError(get_translator()("admin.users.error.role_name"))

    def validate_name_en(self, field: StringField) -> None:
        """Allow an empty English name, but not a long one."""
        if len(_clean(field)) > MAX_ROLE_NAME_LENGTH:
            raise ValidationError(get_translator()("admin.users.error.role_name"))
