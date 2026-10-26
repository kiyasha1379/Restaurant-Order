"""Form fields shared by several admin forms."""

import re
from collections.abc import Sequence

from wtforms import IntegerField

from restaurant.formatting import to_latin_digits
from restaurant.language_context import get_translator

_SEPARATORS = re.compile(r"[\s,٬،.]")


class WholeNumberField(IntegerField):
    """A whole number that accepts Persian digits and thousands separators ("۱۲۰٬۰۰۰")."""

    def process_formdata(self, valuelist: Sequence[str]) -> None:
        """Read the text; an empty or broken value becomes a message in the page language."""
        if not valuelist or not valuelist[0].strip():
            self.data = None
            return
        text = _SEPARATORS.sub("", to_latin_digits(valuelist[0]))
        if not text.isdecimal():
            self.data = None
            raise ValueError(get_translator()("admin.error.number"))
        self.data = int(text)
