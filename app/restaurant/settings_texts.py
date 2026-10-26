"""Interface texts of the admin Settings page and of the ordering pause."""

from restaurant.constants import LANGUAGE_CODE_ENGLISH as EN
from restaurant.constants import LANGUAGE_CODE_PERSIAN as FA

SETTINGS_TEXTS: dict[str, dict[str, str]] = {
    # Public: the pause
    "ordering.paused_badge": {FA: "توقف موقت", EN: "Paused"},
    "ordering.paused_message": {
        FA: "سفارش آنلاین موقتاً متوقف است. لطفاً کمی بعد دوباره سر بزنید.",
        EN: "Online ordering is paused for now. Please check back shortly.",
    },
    "ordering.paused": {
        FA: "سفارش آنلاین موقتاً متوقف است.",
        EN: "Online ordering is paused right now.",
    },
    # Admin
    "admin.nav.settings": {FA: "تنظیمات", EN: "Settings"},
    "admin.settings.title": {FA: "تنظیمات", EN: "Settings"},
    "admin.settings.fa": {FA: "فارسی", EN: "Persian"},
    "admin.settings.en": {FA: "انگلیسی", EN: "English"},
    "admin.settings.ordering": {FA: "سفارش آنلاین", EN: "Online ordering"},
    "admin.settings.pause": {FA: "سفارش آنلاین را موقتاً متوقف کن", EN: "Pause online ordering"},
    "admin.settings.pause_hint": {
        FA: (
            "تا وقتی روشن است مشتری‌ها چیزی به سبد اضافه نمی‌کنند و سفارش ثبت "
            "نمی‌شود؛ سفارش‌های قبلی و رزرو میز ادامه دارند."
        ),
        EN: (
            "While on, customers cannot add dishes or place orders; existing orders "
            "and table booking carry on."
        ),
    },
    "admin.settings.pause_message": {FA: "پیام توقف", EN: "Pause message"},
    "admin.settings.delivery_fee": {FA: "هزینه‌ی ارسال (تومان)", EN: "Delivery fee (toman)"},
    "admin.settings.delivery_fee_hint": {
        FA: "مبلغ ثابت برای هر سفارش ارسالی؛ تحویل حضوری رایگان است.",
        EN: "One fixed amount for every delivery; takeaway is free.",
    },
    "admin.settings.payments": {FA: "روش‌های پرداخت", EN: "Payment methods"},
    "admin.settings.cash_payment": {FA: "پرداخت در محل", EN: "Pay on arrival"},
    "admin.settings.online_payment": {FA: "پرداخت آنلاین", EN: "Pay online"},
    "admin.settings.payments_hint": {
        FA: (
            "دست‌کم یکی از دو روش باید روشن بماند. پرداخت آنلاین به درگاه تنظیم‌شده "
            "در سرور هم نیاز دارد."
        ),
        EN: (
            "At least one method must stay on. Online payment also needs the "
            "gateway set up on the server."
        ),
    },
    "admin.settings.contact": {FA: "اطلاعات تماس", EN: "Contact details"},
    "admin.settings.contact_hint": {
        FA: "در پایین همه‌ی صفحه‌های سایت نمایش داده می‌شود.",
        EN: "Shown at the bottom of every page of the site.",
    },
    "admin.settings.phone": {FA: "شماره‌ی تماس", EN: "Phone number"},
    "admin.settings.address": {FA: "آدرس", EN: "Address"},
    "admin.settings.hours": {FA: "ساعت کاری (متن)", EN: "Opening hours (text)"},
    "admin.settings.booking": {FA: "ساعت کاری و رزرو", EN: "Opening hours and booking"},
    "admin.settings.booking_hint": {
        FA: (
            "ساعت باز بودن هر روز، روزهای تعطیل و قانون‌های رزرو میز در بخش «میزها "
            "و رزروها» تنظیم می‌شود."
        ),
        EN: (
            "Opening hours for each day, closure days and the booking rules live in "
            "the Tables and reservations section."
        ),
    },
    "admin.settings.booking_link": {FA: "ساعت‌ها و قانون‌های رزرو", EN: "Hours and booking rules"},
    "admin.settings.error.delivery_fee": {
        FA: "هزینه‌ی ارسال باید عددی بین ۰ و ۱۰٬۰۰۰٬۰۰۰ تومان باشد.",
        EN: "The delivery fee must be a number between 0 and 10,000,000 toman.",
    },
    "admin.settings.error.no_payment": {
        FA: "دست‌کم یک روش پرداخت باید روشن بماند.",
        EN: "At least one payment method must stay on.",
    },
    "admin.settings.error.phone": {
        FA: "شماره‌ی تماس فقط می‌تواند رقم، + ، - ، پرانتز و فاصله داشته باشد (حداکثر ۴۰ نویسه).",
        EN: (
            "The phone number may only hold digits, +, -, brackets and spaces (40 "
            "characters at most)."
        ),
    },
    "admin.settings.error.too_long": {
        FA: "یکی از متن‌ها بیش از حد طولانی است.",
        EN: "One of the texts is too long.",
    },
}
