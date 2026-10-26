"""The admin Settings form. Messages follow the panel language."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, TextAreaField

from restaurant.constants import LANGUAGE_CODE_ENGLISH as EN
from restaurant.constants import LANGUAGE_CODE_PERSIAN as FA
from restaurant.forms.fields import WholeNumberField
from restaurant.services import (
    ContactDetails,
    InvalidSettingError,
    OrderingSettings,
    SettingsData,
)

PROBLEM_MESSAGES = {
    ("delivery_fee", "range"): "admin.settings.error.delivery_fee",
    ("payment", "none_enabled"): "admin.settings.error.no_payment",
    ("phone", "format"): "admin.settings.error.phone",
    ("address", "length"): "admin.settings.error.too_long",
    ("hours", "length"): "admin.settings.error.too_long",
    ("pause_message", "length"): "admin.settings.error.too_long",
}


class SettingsForm(FlaskForm):
    """Delivery fee, payment methods, the ordering pause and the contact details."""

    delivery_fee = WholeNumberField()
    online_payment = BooleanField()
    cash_payment = BooleanField()
    ordering_paused = BooleanField()
    pause_message_fa = TextAreaField()
    pause_message_en = TextAreaField()
    phone = StringField()
    address_fa = StringField()
    address_en = StringField()
    hours_fa = StringField()
    hours_en = StringField()

    def fill(self, data: SettingsData) -> None:
        """Show the stored settings in the form."""
        self.delivery_fee.data = data.ordering.delivery_fee
        self.online_payment.data = data.ordering.online_payment
        self.cash_payment.data = data.ordering.cash_payment
        self.ordering_paused.data = data.ordering.paused
        contact = data.contact
        self.pause_message_fa.data = contact.pause_message[FA]
        self.pause_message_en.data = contact.pause_message[EN]
        self.phone.data = contact.phone
        self.address_fa.data = contact.address[FA]
        self.address_en.data = contact.address[EN]
        self.hours_fa.data = contact.hours[FA]
        self.hours_en.data = contact.hours[EN]

    def to_data(self) -> SettingsData:
        """Return what the form holds as service input (call after validation)."""
        return SettingsData(
            ordering=OrderingSettings(
                delivery_fee=self.delivery_fee.data,
                online_payment=self.online_payment.data,
                cash_payment=self.cash_payment.data,
                paused=self.ordering_paused.data,
            ),
            contact=ContactDetails(
                phone=(self.phone.data or "").strip(),
                address={FA: self.address_fa.data or "", EN: self.address_en.data or ""},
                hours={FA: self.hours_fa.data or "", EN: self.hours_en.data or ""},
                pause_message={
                    FA: self.pause_message_fa.data or "",
                    EN: self.pause_message_en.data or "",
                },
            ),
        )

    def show_problem(self, problem: InvalidSettingError, translate) -> None:  # noqa: ANN001
        """Put a refused value next to its field as a message in the panel language."""
        message = translate(PROBLEM_MESSAGES[(problem.field, problem.problem)])
        target = {
            "delivery_fee": self.delivery_fee,
            "payment": self.cash_payment,
            "phone": self.phone,
            "address": self.address_fa,
            "hours": self.hours_fa,
            "pause_message": self.pause_message_fa,
        }[problem.field]
        target.errors = [*target.errors, message]
