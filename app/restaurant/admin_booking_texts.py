"""Admin panel texts for tables and reservations in both languages."""

from restaurant.constants import LANGUAGE_CODE_ENGLISH as EN
from restaurant.constants import LANGUAGE_CODE_PERSIAN as FA

ADMIN_BOOKING_TEXTS: dict[str, dict[str, str]] = {
    "admin.nav.tables": {FA: "میزها و رزروها", EN: "Tables and reservations"},
    "admin.reservations.title": {FA: "رزروها", EN: "Reservations"},
    "admin.reservations.tab_list": {FA: "رزروها", EN: "Bookings"},
    "admin.reservations.tab_tables": {FA: "میزها", EN: "Tables"},
    "admin.reservations.tab_schedule": {FA: "ساعت کاری و قوانین", EN: "Hours and rules"},
    "admin.reservations.new": {FA: "رزرو دستی", EN: "New booking"},
    "admin.reservations.day": {FA: "روز", EN: "Day"},
    "admin.reservations.upcoming": {FA: "از امروز به بعد", EN: "From today on"},
    "admin.reservations.pick_day": {FA: "انتخاب روز", EN: "Choose a day"},
    "admin.reservations.filter": {FA: "نمایش", EN: "Show"},
    "admin.reservations.clear": {FA: "همه‌ی روزها", EN: "All days"},
    "admin.reservations.all": {FA: "همه", EN: "All"},
    "admin.reservations.waiting": {
        FA: "{count} رزرو منتظر پاسخ است.",
        EN: "{count} booking(s) waiting for an answer.",
    },
    "admin.reservations.number": {FA: "شماره", EN: "No."},
    "admin.reservations.when": {FA: "زمان", EN: "When"},
    "admin.reservations.guests": {FA: "نفرات", EN: "Guests"},
    "admin.reservations.table": {FA: "میز", EN: "Table"},
    "admin.reservations.guest": {FA: "مهمان", EN: "Guest"},
    "admin.reservations.phone": {FA: "تلفن", EN: "Phone"},
    "admin.reservations.note": {FA: "توضیحات", EN: "Notes"},
    "admin.reservations.status": {FA: "وضعیت", EN: "Status"},
    "admin.reservations.view": {FA: "نمایش", EN: "View"},
    "admin.reservations.confirm": {FA: "تأیید", EN: "Confirm"},
    "admin.reservations.cancel": {FA: "لغو رزرو", EN: "Cancel booking"},
    "admin.reservations.cancel_confirm": {
        FA: "این رزرو لغو شود؟",
        EN: "Cancel this booking?",
    },
    "admin.reservations.empty": {FA: "رزروی پیدا نشد.", EN: "No bookings found."},
    "admin.reservations.source_guest": {FA: "ثبت‌شده توسط مهمان", EN: "Made by the guest"},
    "admin.reservations.created": {FA: "زمان ثبت", EN: "Made at"},
    "admin.reservations.move_title": {FA: "جابه‌جایی به میز دیگر", EN: "Move to another table"},
    "admin.reservations.move_hint": {
        FA: "میزهای خالی که برای این تعداد نفر و این زمان مناسب‌اند:",
        EN: "Free tables that fit this party at this time:",
    },
    "admin.reservations.move_none": {
        FA: "میز خالی مناسبی برای این زمان نیست.",
        EN: "No free table fits this time.",
    },
    "admin.reservations.move_here": {FA: "انتقال به میز {label}", EN: "Move to table {label}"},
    "admin.reservations.form_time": {FA: "ساعت شروع", EN: "Start time"},
    "admin.reservations.form_status": {FA: "وضعیت اولیه", EN: "Starting status"},
    "admin.reservations.form_hint": {
        FA: (
            "کارکنان می‌توانند هر ساعتی را در ساعت کاری انتخاب "
            "کنند؛ شرط فاصله‌ی ساعت‌ها و حداقل زمان قبل اعمال نمی‌شود."
        ),
        EN: (
            "Staff may pick any time inside opening hours; "
            "the start-time grid and notice time do not apply."
        ),
    },
    "admin.reservations.save": {FA: "ثبت رزرو", EN: "Save booking"},
    "admin.reservations.error.range": {
        FA: "عدد باید در بازه‌ی مجاز باشد.",
        EN: "The number must be inside the allowed range.",
    },
    "admin.tables.title": {FA: "میزهای سالن", EN: "Tables of the hall"},
    "admin.tables.add": {FA: "افزودن میز", EN: "Add a table"},
    "admin.tables.edit": {FA: "ویرایش میز", EN: "Edit table"},
    "admin.tables.label": {FA: "شماره یا نام میز", EN: "Table number or name"},
    "admin.tables.capacity": {FA: "ظرفیت (نفر)", EN: "Seats"},
    "admin.tables.order": {FA: "ترتیب در نقشه", EN: "Order on the plan"},
    "admin.tables.active": {FA: "قابل رزرو", EN: "Open for booking"},
    "admin.tables.inactive": {FA: "خارج از سرویس", EN: "Out of use"},
    "admin.tables.bookings": {FA: "رزروهای پیش‌رو", EN: "Bookings ahead"},
    "admin.tables.take_out": {FA: "خارج کردن از سرویس", EN: "Take out of use"},
    "admin.tables.put_back": {FA: "برگرداندن به سرویس", EN: "Put back in use"},
    "admin.tables.move_up": {FA: "بالا بردن", EN: "Move up"},
    "admin.tables.move_down": {FA: "پایین بردن", EN: "Move down"},
    "admin.tables.delete_confirm": {FA: "این میز حذف شود؟", EN: "Delete this table?"},
    "admin.tables.empty": {FA: "هنوز میزی ثبت نشده است.", EN: "No tables yet."},
    "admin.tables.hint": {
        FA: (
            "رزروهای گذشته برچسب میز را نگه می‌دارند، پس "
            "حذف یا تغییر نام میز آنها را خراب نمی‌کند."
        ),
        EN: (
            "Past bookings keep the table label, so deleting "
            "or renaming a table does not break them."
        ),
    },
    "admin.tables.error.label": {
        FA: "نام میز را وارد کنید (حداکثر ۲۰ نویسه) و ظرفیت را بین ۱ تا ۵۰ بگذارید.",
        EN: "Enter a table name (up to 20 characters) and 1 to 50 seats.",
    },
    "admin.tables.error.duplicate": {
        FA: "میز دیگری با همین نام وجود دارد.",
        EN: "Another table already has this name.",
    },
    "admin.tables.error.in_use": {
        FA: "این میز رزرو فعال پیش‌رو دارد. اول رزروها را لغو یا منتقل کنید.",
        EN: "This table still has live bookings ahead. Cancel or move them first.",
    },
    "admin.schedule.hours": {FA: "ساعت کاری هفته", EN: "Weekly opening hours"},
    "admin.schedule.opens": {FA: "ساعت باز شدن", EN: "Opens"},
    "admin.schedule.closes": {FA: "ساعت بسته شدن", EN: "Closes"},
    "admin.schedule.closed": {FA: "تعطیل", EN: "Closed"},
    "admin.schedule.weekday": {FA: "روز هفته", EN: "Weekday"},
    "admin.schedule.save_hours": {FA: "ذخیره‌ی ساعت‌ها", EN: "Save hours"},
    "admin.schedule.closures": {FA: "روزهای تعطیل خاص", EN: "Special closing days"},
    "admin.schedule.closure_hint": {
        FA: "روزی را که رستوران بسته است انتخاب کنید؛ در آن روز رزرو گرفته نمی‌شود.",
        EN: "Choose a day the restaurant is closed; no bookings are taken on it.",
    },
    "admin.schedule.reason": {FA: "دلیل (اختیاری)", EN: "Reason (optional)"},
    "admin.schedule.add_closure": {FA: "تعطیل کردن این روز", EN: "Close this day"},
    "admin.schedule.no_closures": {
        FA: "روز تعطیل خاصی ثبت نشده است.",
        EN: "No special closing days.",
    },
    "admin.schedule.reopen": {FA: "باز کردن دوباره", EN: "Open again"},
    "admin.schedule.error.hours": {
        FA: "ساعت بسته شدن باید بعد از ساعت باز شدن باشد و هر دو ساعت باید درست وارد شوند.",
        EN: "Closing must be later than opening, and both times must be filled in.",
    },
    "admin.schedule.error.duplicate": {
        FA: "این روز قبلاً تعطیل شده است.",
        EN: "This day is already closed.",
    },
    "admin.rules.title": {FA: "قوانین رزرو", EN: "Reservation rules"},
    "admin.rules.max_advance_days": {FA: "حداکثر روز پیش از موعد", EN: "Book up to (days ahead)"},
    "admin.rules.duration_minutes": {FA: "مدت نشستن (دقیقه)", EN: "Stay length (minutes)"},
    "admin.rules.slot_minutes": {
        FA: "فاصله‌ی ساعت‌های شروع (دقیقه)",
        EN: "Start-time step (minutes)",
    },
    "admin.rules.min_notice_minutes": {
        FA: "حداقل زمان قبل از شروع (دقیقه)",
        EN: "Minimum notice (minutes)",
    },
    "admin.rules.auto_confirm": {
        FA: "رزروها خودکار تأیید شوند",
        EN: "Confirm bookings automatically",
    },
    "admin.rules.auto_confirm_hint": {
        FA: "اگر خاموش باشد، هر رزرو منتظر تأیید کارکنان می‌ماند.",
        EN: "When off, every booking waits for staff to confirm it.",
    },
    "admin.rules.save": {FA: "ذخیره‌ی قوانین", EN: "Save rules"},
}
