"""Forms of the customer area: sign-in, registration, code, profile, addresses, contact."""

import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, TextAreaField
from wtforms.validators import ValidationError

from restaurant.constants import MIN_PASSWORD_LENGTH
from restaurant.formatting import to_latin_digits
from restaurant.language_context import get_translator
from restaurant.phone import normalize_mobile
from restaurant.services.contact_service import (
    MAX_BODY_LENGTH,
    MIN_BODY_LENGTH,
)
from restaurant.services.customer_profile_service import (
    MAX_ADDRESS_LENGTH,
    MAX_LABEL_LENGTH,
    MAX_NAME_LENGTH,
    MIN_NAME_LENGTH,
)

MIN_ADDRESS_LENGTH = 10
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _text(key: str) -> str:
    """Return an interface text in the page language."""
    return get_translator()(key)


def _clean_name(field: StringField) -> None:
    """Trim a person's name and require a sensible length."""
    field.data = (field.data or "").strip()
    if not MIN_NAME_LENGTH <= len(field.data) <= MAX_NAME_LENGTH:
        raise ValidationError(_text("account.error.name"))


def _clean_phone(field: StringField) -> None:
    """Require an Iranian mobile number and store it in its clean form."""
    number = normalize_mobile(field.data or "")
    if number is None:
        raise ValidationError(_text("account.error.phone"))
    field.data = number


def _clean_optional_email(field: StringField) -> None:
    """Allow an empty e-mail, otherwise require a plausible address."""
    field.data = (field.data or "").strip().lower()
    if field.data and not _EMAIL_PATTERN.match(field.data):
        raise ValidationError(_text("account.error.email"))


def _check_new_password(field: PasswordField) -> None:
    """Require the minimum password length."""
    if len(field.data or "") < MIN_PASSWORD_LENGTH:
        raise ValidationError(_text("account.error.password_short"))


class SignInForm(FlaskForm):
    """Sign in with a phone number or e-mail and a password."""

    identifier = StringField()
    password = PasswordField()

    def validate_identifier(self, field: StringField) -> None:
        """Require something to look up."""
        field.data = (field.data or "").strip()
        if not field.data:
            raise ValidationError(_text("account.error.identifier"))

    def validate_password(self, field: PasswordField) -> None:
        """Require a password."""
        if not field.data:
            raise ValidationError(_text("account.error.password_missing"))


class RegisterForm(FlaskForm):
    """Create an account: name, mobile number, optional e-mail and a password."""

    customer_name = StringField()
    phone = StringField()
    email = StringField()
    password = PasswordField()
    password_again = PasswordField()

    def validate_customer_name(self, field: StringField) -> None:
        """Require a name."""
        _clean_name(field)

    def validate_phone(self, field: StringField) -> None:
        """Require a mobile number."""
        _clean_phone(field)

    def validate_email(self, field: StringField) -> None:
        """Check the optional e-mail."""
        _clean_optional_email(field)

    def validate_password(self, field: PasswordField) -> None:
        """Require a long enough password."""
        _check_new_password(field)

    def validate_password_again(self, field: PasswordField) -> None:
        """Require the same password twice."""
        if field.data != self.password.data:
            raise ValidationError(_text("account.error.password_mismatch"))


class VerifyForm(FlaskForm):
    """The code sent to the phone."""

    code = StringField()

    def validate_code(self, field: StringField) -> None:
        """Accept Persian digits and keep only the digits."""
        field.data = re.sub(r"\D", "", to_latin_digits(field.data or ""))
        if not field.data:
            raise ValidationError(_text("account.error.code_missing"))


class ProfileForm(FlaskForm):
    """Change the name and the e-mail address."""

    customer_name = StringField()
    email = StringField()

    def validate_customer_name(self, field: StringField) -> None:
        """Require a name."""
        _clean_name(field)

    def validate_email(self, field: StringField) -> None:
        """Check the optional e-mail."""
        _clean_optional_email(field)


class PasswordForm(FlaskForm):
    """Change the password; the current one must be typed again."""

    current_password = PasswordField()
    new_password = PasswordField()
    new_password_again = PasswordField()

    def validate_current_password(self, field: PasswordField) -> None:
        """Require the current password."""
        if not field.data:
            raise ValidationError(_text("account.error.password_missing"))

    def validate_new_password(self, field: PasswordField) -> None:
        """Require a long enough password."""
        _check_new_password(field)

    def validate_new_password_again(self, field: PasswordField) -> None:
        """Require the same password twice."""
        if field.data != self.new_password.data:
            raise ValidationError(_text("account.error.password_mismatch"))


class AddressForm(FlaskForm):
    """One address of the address book."""

    label = StringField()
    text = TextAreaField()
    is_default = BooleanField()

    def validate_label(self, field: StringField) -> None:
        """Keep the label short."""
        field.data = (field.data or "").strip()
        if len(field.data) > MAX_LABEL_LENGTH:
            raise ValidationError(_text("account.error.label"))

    def validate_text(self, field: TextAreaField) -> None:
        """Require a real address."""
        field.data = (field.data or "").strip()
        if not MIN_ADDRESS_LENGTH <= len(field.data) <= MAX_ADDRESS_LENGTH:
            raise ValidationError(_text("account.error.address"))


class ContactForm(FlaskForm):
    """The contact form on the public site."""

    customer_name = StringField()
    contact = StringField()
    body = TextAreaField()

    def validate_customer_name(self, field: StringField) -> None:
        """Require a name."""
        _clean_name(field)

    def validate_contact(self, field: StringField) -> None:
        """Require a phone number or an e-mail address to answer to."""
        field.data = (field.data or "").strip()
        phone = normalize_mobile(field.data)
        if phone is not None:
            field.data = phone
            return
        if not _EMAIL_PATTERN.match(field.data.lower()):
            raise ValidationError(_text("contact.error.contact"))
        field.data = field.data.lower()

    def validate_body(self, field: TextAreaField) -> None:
        """Require a message of a sensible length."""
        field.data = (field.data or "").strip()
        if not MIN_BODY_LENGTH <= len(field.data) <= MAX_BODY_LENGTH:
            raise ValidationError(_text("contact.error.body"))
