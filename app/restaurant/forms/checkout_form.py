"""The checkout form: who is ordering, how they get it and how they pay."""

from flask_wtf import FlaskForm
from wtforms import RadioField, StringField, TextAreaField
from wtforms.fields.choices import SelectChoice
from wtforms.validators import ValidationError

from restaurant.constants import FulfillmentType, PaymentMethod
from restaurant.language_context import get_translator
from restaurant.phone import normalize_mobile

MIN_NAME_LENGTH = 2
MAX_NAME_LENGTH = 120
MIN_ADDRESS_LENGTH = 10
MAX_ADDRESS_LENGTH = 500
MAX_NOTE_LENGTH = 500


class CheckoutForm(FlaskForm):
    """Checkout details; error messages follow the page language."""

    customer_name = StringField()
    customer_phone = StringField()
    fulfillment = RadioField(
        choices=[SelectChoice(member.value, member.value) for member in FulfillmentType],
        default=FulfillmentType.TAKEAWAY.value,
    )
    delivery_address = TextAreaField()
    note = TextAreaField()
    payment_method = RadioField(
        choices=[SelectChoice(PaymentMethod.CASH_ON_SITE.value, PaymentMethod.CASH_ON_SITE.value)],
        default=PaymentMethod.CASH_ON_SITE.value,
    )

    def validate_customer_name(self, field: StringField) -> None:
        """Require a name of a sensible length."""
        field.data = (field.data or "").strip()
        if not MIN_NAME_LENGTH <= len(field.data) <= MAX_NAME_LENGTH:
            raise ValidationError(get_translator()("checkout.error.name"))

    def validate_customer_phone(self, field: StringField) -> None:
        """Require an Iranian mobile number and store it in its clean form."""
        number = normalize_mobile(field.data or "")
        if number is None:
            raise ValidationError(get_translator()("checkout.error.phone"))
        field.data = number

    def validate_delivery_address(self, field: TextAreaField) -> None:
        """Require an address only when the order is delivered."""
        field.data = (field.data or "").strip()
        if self.fulfillment.data != FulfillmentType.DELIVERY.value:
            return
        if not MIN_ADDRESS_LENGTH <= len(field.data) <= MAX_ADDRESS_LENGTH:
            raise ValidationError(get_translator()("checkout.error.address"))

    def validate_note(self, field: TextAreaField) -> None:
        """Keep the note short."""
        field.data = (field.data or "").strip()
        if len(field.data) > MAX_NOTE_LENGTH:
            raise ValidationError(get_translator()("checkout.error.note"))

    @property
    def fulfillment_type(self) -> FulfillmentType:
        """The chosen way of receiving the order, as an enum."""
        return FulfillmentType(self.fulfillment.data)

    @property
    def chosen_payment_method(self) -> PaymentMethod:
        """The chosen way of paying, as an enum."""
        return PaymentMethod(self.payment_method.data)
