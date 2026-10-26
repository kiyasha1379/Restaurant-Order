"""Interface texts of the builder pages (pizza, sandwich, drink) in both languages."""

from restaurant.constants import LANGUAGE_CODE_ENGLISH as EN
from restaurant.constants import LANGUAGE_CODE_PERSIAN as FA

BUILDER_TEXTS: dict[str, dict[str, str]] = {
    "builder.title": {FA: "ساخت دلخواه", EN: "Build your own"},
    "builder.subtitle": {
        FA: "خودتان بسازید، تعدادش را بگویید و به سبد اضافه کنید.",
        EN: "Build it yourself, pick how many, and add it to your cart.",
    },
    "builder.tabs_label": {FA: "نوع ساخت", EN: "What to build"},
    "builder.empty": {
        FA: "هنوز چیزی برای ساختن آماده نیست.",
        EN: "There is nothing to build yet.",
    },
    "builder.hint.single": {FA: "یکی را انتخاب کنید", EN: "Choose one"},
    "builder.hint.multiple": {FA: "هر چند تا خواستید", EN: "As many as you like"},
    "builder.hint.optional": {FA: "اختیاری", EN: "Optional"},
    "builder.free": {FA: "رایگان", EN: "Free"},
    "builder.sold_out": {FA: "تمام شد", EN: "Sold out"},
    "builder.steps_label": {FA: "مراحل ساخت", EN: "Build steps"},
    "builder.preview_label": {FA: "پیش‌نمایش {name}", EN: "Preview of your {name}"},
    "builder.layers.title": {FA: "ترتیب لایه‌ها", EN: "Layer order"},
    "builder.layers.hint": {
        FA: "از بالا به پایین؛ با فلش‌ها جابه‌جا کنید",
        EN: "Top to bottom; use the arrows to move",
    },
    "builder.layers.empty": {
        FA: "هنوز ماده‌ای انتخاب نکرده‌اید. از مراحل بالا چیزی اضافه کنید تا اینجا ببینید.",
        EN: "You have not picked a filling yet. Add something above to see it here.",
    },
    "builder.layers.top": {FA: "{name} (بالا)", EN: "{name} (top)"},
    "builder.layers.bottom": {FA: "{name} (پایین)", EN: "{name} (bottom)"},
    "builder.layers.fixed": {FA: "ثابت", EN: "Fixed"},
    "builder.layers.up": {FA: "بالا بردن {name}", EN: "Move {name} up"},
    "builder.layers.down": {FA: "پایین بردن {name}", EN: "Move {name} down"},
    "builder.summary.title": {FA: "خلاصه‌ی انتخاب شما", EN: "Your build"},
    "builder.summary.none": {FA: "بدون انتخاب", EN: "None chosen"},
    "builder.unit_price": {FA: "قیمت هر عدد", EN: "Price each"},
    "builder.quantity": {FA: "تعداد", EN: "Quantity"},
    "builder.quantity_up": {FA: "یکی بیشتر", EN: "One more"},
    "builder.quantity_down": {FA: "یکی کمتر", EN: "One less"},
    "builder.total": {FA: "جمع", EN: "Total"},
    "builder.add": {FA: "افزودن به سبد", EN: "Add to cart"},
    "builder.view_cart": {FA: "رفتن به سبد خرید", EN: "Go to cart"},
    "builder.missing_step": {FA: "مرحله‌ی «{step}» را انتخاب کنید.", EN: "Choose “{step}” first."},
    "builder.error.unknown": {
        FA: "این ترکیب معتبر نیست. صفحه را دوباره باز کنید.",
        EN: "This combination is not valid. Please reload the page.",
    },
    "builder.error.unavailable": {
        FA: "یکی از موارد انتخابی دیگر موجود نیست.",
        EN: "One of the chosen items is no longer available.",
    },
    "builder.error.too_many": {
        FA: "در یکی از مرحله‌ها فقط می‌شود یک مورد انتخاب کرد.",
        EN: "Only one item can be chosen in one of the steps.",
    },
    "builder.error.missing": {
        FA: "مرحله‌های لازم را کامل کنید.",
        EN: "Please complete the required steps.",
    },
}
