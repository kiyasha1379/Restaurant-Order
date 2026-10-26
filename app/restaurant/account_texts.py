"""Interface texts of the customer area and the contact page in both languages."""

from restaurant.constants import LANGUAGE_CODE_ENGLISH as EN
from restaurant.constants import LANGUAGE_CODE_PERSIAN as FA

ACCOUNT_TEXTS: dict[str, dict[str, str]] = {
    "header.account": {FA: "حساب من", EN: "My account"},
    "account.logout": {FA: "خروج", EN: "Sign out"},
    "account.signed_out": {FA: "از حساب خود خارج شدید.", EN: "You have been signed out."},
    "account.welcome": {FA: "خوش آمدید، {name}!", EN: "Welcome, {name}!"},
    "account.verified": {
        FA: "حساب شما تأیید شد. خوش آمدید، {name}!",
        EN: "Your account is verified. Welcome, {name}!",
    },
    # Sign in
    "account.login.title": {FA: "ورود به حساب", EN: "Sign in"},
    "account.login.subtitle": {
        FA: "با شماره موبایل یا ایمیل وارد شوید تا سفارش‌ها و رزروهایتان را ببینید.",
        EN: "Sign in with your mobile number or e-mail to see your orders and bookings.",
    },
    "account.login.identifier": {FA: "شماره موبایل یا ایمیل", EN: "Mobile number or e-mail"},
    "account.login.password": {FA: "رمز عبور", EN: "Password"},
    "account.login.submit": {FA: "ورود", EN: "Sign in"},
    "account.login.no_account": {FA: "حساب ندارید؟", EN: "No account yet?"},
    "account.login.register_link": {FA: "ثبت‌نام کنید", EN: "Create one"},
    "account.login.cart_note": {
        FA: "سبد خریدتان بعد از ورود همین‌جا می‌ماند.",
        EN: "Your cart stays as it is after you sign in.",
    },
    "account.login.error.invalid": {
        FA: "شماره یا ایمیل یا رمز عبور درست نیست.",
        EN: "The number, e-mail or password is not right.",
    },
    "account.login.error.blocked": {
        FA: "این حساب مسدود شده است. با رستوران تماس بگیرید.",
        EN: "This account is blocked. Please contact the restaurant.",
    },
    # Registration
    "account.register.title": {FA: "ساخت حساب", EN: "Create an account"},
    "account.register.subtitle": {
        FA: "با یک حساب، سفارش دوباره و رزرو سریع‌تر می‌شود.",
        EN: "With an account, ordering again and booking get faster.",
    },
    "account.register.name": {FA: "نام و نام خانوادگی", EN: "Full name"},
    "account.register.phone": {FA: "شماره موبایل", EN: "Mobile number"},
    "account.register.phone_hint": {
        FA: "کد تأیید به این شماره فرستاده می‌شود.",
        EN: "A verification code is sent to this number.",
    },
    "account.register.email": {FA: "ایمیل (اختیاری)", EN: "E-mail (optional)"},
    "account.register.password": {FA: "رمز عبور", EN: "Password"},
    "account.register.password_hint": {
        FA: "دست‌کم ۸ نویسه.",
        EN: "At least 8 characters.",
    },
    "account.register.password_again": {FA: "تکرار رمز عبور", EN: "Repeat the password"},
    "account.register.submit": {FA: "ثبت‌نام و دریافت کد", EN: "Sign up and get a code"},
    "account.register.have_account": {FA: "قبلاً ثبت‌نام کرده‌اید؟", EN: "Already registered?"},
    "account.register.login_link": {FA: "وارد شوید", EN: "Sign in"},
    "account.register.error.phone_taken": {
        FA: "با این شماره قبلاً حساب ساخته شده است. وارد شوید.",
        EN: "An account with this number already exists. Please sign in.",
    },
    "account.register.error.email_taken": {
        FA: "با این ایمیل قبلاً حساب ساخته شده است.",
        EN: "An account with this e-mail already exists.",
    },
    # Verification code
    "account.verify.title": {FA: "تأیید شماره موبایل", EN: "Verify your number"},
    "account.verify.subtitle": {
        FA: "کد ۵ رقمی فرستاده‌شده به {phone} را وارد کنید.",
        EN: "Type the 5-digit code sent to {phone}.",
    },
    "account.verify.code": {FA: "کد تأیید", EN: "Verification code"},
    "account.verify.submit": {FA: "تأیید", EN: "Verify"},
    "account.verify.resend": {FA: "ارسال دوباره‌ی کد", EN: "Send the code again"},
    "account.verify.resent": {FA: "کد تازه فرستاده شد.", EN: "A new code was sent."},
    "account.verify.demo_hint": {
        FA: "نسخهٔ نمایشی: پیامکی فرستاده نمی‌شود؛ کد تأیید {code} است.",
        EN: "Demo version: no SMS is sent; the code is {code}.",
    },
    "account.verify.wrong": {
        FA: "کد درست نیست. دوباره امتحان کنید.",
        EN: "That code is not right. Please try again.",
    },
    "account.verify.expired": {
        FA: "کد منقضی شده است. کد تازه بگیرید.",
        EN: "The code has expired. Please ask for a new one.",
    },
    "account.verify.too_many": {
        FA: "تعداد تلاش‌ها زیاد بود. کد تازه بگیرید.",
        EN: "Too many tries. Please ask for a new code.",
    },
    # Form errors
    "account.error.name": {
        FA: "نام را بنویسید (دست‌کم ۲ حرف).",
        EN: "Enter a name (2 letters or more).",
    },
    "account.error.phone": {
        FA: "شماره موبایل معتبر نیست؛ مثلاً ۰۹۱۲۳۴۵۶۷۸۹.",
        EN: "That is not a valid mobile number, for example 09123456789.",
    },
    "account.error.email": {FA: "ایمیل معتبر نیست.", EN: "That e-mail address is not valid."},
    "account.error.identifier": {
        FA: "شماره موبایل یا ایمیل را بنویسید.",
        EN: "Enter your mobile number or e-mail.",
    },
    "account.error.password_missing": {FA: "رمز عبور را بنویسید.", EN: "Enter the password."},
    "account.error.password_short": {
        FA: "رمز عبور دست‌کم ۸ نویسه باشد.",
        EN: "The password needs at least 8 characters.",
    },
    "account.error.password_mismatch": {
        FA: "دو رمز عبور یکی نیستند.",
        EN: "The two passwords do not match.",
    },
    "account.error.code_missing": {FA: "کد را بنویسید.", EN: "Enter the code."},
    "account.error.label": {FA: "عنوان خیلی بلند است.", EN: "The title is too long."},
    "account.error.address": {
        FA: "آدرس را کامل بنویسید (۱۰ تا ۵۰۰ نویسه).",
        EN: "Write the full address (10 to 500 characters).",
    },
    # Account pages
    "account.title": {FA: "حساب من", EN: "My account"},
    "account.hello": {FA: "سلام، {name}", EN: "Hello, {name}"},
    "account.nav.label": {FA: "بخش‌های حساب", EN: "Account sections"},
    "account.nav.overview": {FA: "خلاصه", EN: "Overview"},
    "account.nav.orders": {FA: "سفارش‌ها", EN: "Orders"},
    "account.nav.reservations": {FA: "رزروها", EN: "Bookings"},
    "account.nav.addresses": {FA: "آدرس‌ها", EN: "Addresses"},
    "account.nav.profile": {FA: "مشخصات", EN: "Profile"},
    "account.overview.recent_orders": {FA: "آخرین سفارش‌ها", EN: "Recent orders"},
    "account.overview.upcoming": {FA: "رزروهای پیش‌رو", EN: "Upcoming bookings"},
    "account.overview.default_address": {FA: "آدرس اصلی", EN: "Main address"},
    "account.overview.view_all": {FA: "همه", EN: "View all"},
    "account.overview.none_orders": {
        FA: "هنوز سفارشی ثبت نکرده‌اید.",
        EN: "You have not placed an order yet.",
    },
    "account.overview.none_bookings": {
        FA: "رزرو پیش‌رویی ندارید.",
        EN: "You have no upcoming bookings.",
    },
    "account.overview.none_address": {
        FA: "هنوز آدرسی ذخیره نکرده‌اید.",
        EN: "You have not saved an address yet.",
    },
    "account.overview.order_now": {FA: "رفتن به منو", EN: "Go to the menu"},
    # Orders
    "account.orders.title": {FA: "سفارش‌های من", EN: "My orders"},
    "account.orders.empty": {
        FA: "سفارشی ثبت نشده است. از منو شروع کنید.",
        EN: "No orders yet. Start from the menu.",
    },
    "account.orders.number": {FA: "سفارش شماره {number}", EN: "Order {number}"},
    "account.orders.items": {FA: "{count} قلم", EN: "{count} items"},
    "account.orders.track": {FA: "پیگیری", EN: "Track"},
    "account.orders.reorder": {FA: "سفارش دوباره", EN: "Order again"},
    "account.orders.more": {FA: "صفحه‌ی بعد", EN: "Next page"},
    "account.orders.less": {FA: "صفحه‌ی قبل", EN: "Previous page"},
    "account.reorder.done": {
        FA: "{count} مورد به سبد خرید اضافه شد.",
        EN: "{count} items were added to your cart.",
    },
    "account.reorder.skipped": {
        FA: "{count} مورد دیگر الان موجود نیست.",
        EN: "{count} more items are not available right now.",
    },
    "account.reorder.none": {
        FA: "هیچ‌یک از اقلام این سفارش الان موجود نیست.",
        EN: "None of the items of this order is available right now.",
    },
    # Bookings
    "account.reservations.title": {FA: "رزروهای من", EN: "My bookings"},
    "account.reservations.empty": {
        FA: "رزروی ثبت نشده است.",
        EN: "No bookings yet.",
    },
    "account.reservations.book": {FA: "رزرو میز", EN: "Book a table"},
    "account.reservations.view": {FA: "جزئیات", EN: "Details"},
    "account.reservations.table": {FA: "میز {label}", EN: "Table {label}"},
    "account.reservations.guests": {FA: "{count} نفر", EN: "{count} guests"},
    "account.reservations.past": {FA: "رزروهای گذشته", EN: "Past bookings"},
    # Addresses
    "account.addresses.title": {FA: "آدرس‌های من", EN: "My addresses"},
    "account.addresses.empty": {
        FA: "هنوز آدرسی ذخیره نشده است.",
        EN: "No saved addresses yet.",
    },
    "account.addresses.add": {FA: "افزودن آدرس", EN: "Add an address"},
    "account.addresses.edit": {FA: "ویرایش آدرس", EN: "Edit address"},
    "account.addresses.label": {FA: "عنوان (مثلاً خانه)", EN: "Title (for example Home)"},
    "account.addresses.text": {FA: "آدرس کامل", EN: "Full address"},
    "account.addresses.is_default": {FA: "آدرس اصلی باشد", EN: "Make it the main address"},
    "account.addresses.default_badge": {FA: "اصلی", EN: "Main"},
    "account.addresses.save": {FA: "ذخیره", EN: "Save"},
    "account.addresses.edit_button": {FA: "ویرایش", EN: "Edit"},
    "account.addresses.delete": {FA: "حذف", EN: "Delete"},
    "account.addresses.delete_confirm": {FA: "این آدرس حذف شود؟", EN: "Delete this address?"},
    "account.addresses.make_default": {FA: "اصلی کن", EN: "Make main"},
    "account.addresses.cancel": {FA: "انصراف", EN: "Cancel"},
    "account.addresses.saved": {FA: "آدرس ذخیره شد.", EN: "The address was saved."},
    "account.addresses.deleted": {FA: "آدرس حذف شد.", EN: "The address was deleted."},
    "account.addresses.error.too_many": {
        FA: "حداکثر ۱۰ آدرس می‌توانید ذخیره کنید.",
        EN: "You can save up to 10 addresses.",
    },
    "account.addresses.error.unknown": {
        FA: "این آدرس پیدا نشد.",
        EN: "That address was not found.",
    },
    # Profile
    "account.profile.title": {FA: "مشخصات من", EN: "My profile"},
    "account.profile.name": {FA: "نام و نام خانوادگی", EN: "Full name"},
    "account.profile.email": {FA: "ایمیل (اختیاری)", EN: "E-mail (optional)"},
    "account.profile.phone": {FA: "شماره موبایل", EN: "Mobile number"},
    "account.profile.phone_fixed": {
        FA: "شماره موبایل را نمی‌شود تغییر داد.",
        EN: "The mobile number cannot be changed.",
    },
    "account.profile.save": {FA: "ذخیره‌ی تغییرات", EN: "Save changes"},
    "account.profile.saved": {FA: "مشخصات ذخیره شد.", EN: "Your profile was saved."},
    "account.profile.error.email_taken": {
        FA: "این ایمیل برای حساب دیگری است.",
        EN: "This e-mail belongs to another account.",
    },
    "account.password.title": {FA: "تغییر رمز عبور", EN: "Change your password"},
    "account.password.current": {FA: "رمز عبور فعلی", EN: "Current password"},
    "account.password.new": {FA: "رمز عبور تازه", EN: "New password"},
    "account.password.again": {FA: "تکرار رمز عبور تازه", EN: "Repeat the new password"},
    "account.password.submit": {FA: "تغییر رمز", EN: "Change password"},
    "account.password.changed": {FA: "رمز عبور تغییر کرد.", EN: "Your password was changed."},
    "account.password.error.wrong": {
        FA: "رمز عبور فعلی درست نیست.",
        EN: "The current password is not right.",
    },
    # Checkout and booking pages for signed-in customers
    "checkout.saved_addresses": {FA: "آدرس‌های ذخیره‌شده", EN: "Saved addresses"},
    "checkout.save_address": {
        FA: "این آدرس برای دفعه‌ی بعد ذخیره شود",
        EN: "Save this address for next time",
    },
    "checkout.signed_in_as": {FA: "با حساب {name} سفارش می‌دهید.", EN: "Ordering as {name}."},
    "checkout.login_hint": {
        FA: "حساب دارید؟ وارد شوید تا اطلاعاتتان خودکار پر شود.",
        EN: "Have an account? Sign in to fill in your details.",
    },
    "checkout.login_link": {FA: "ورود", EN: "Sign in"},
    # Contact page
    "contact.title": {FA: "تماس با ما", EN: "Contact us"},
    "contact.subtitle": {
        FA: "پیام، پیشنهاد یا انتقادتان را بنویسید؛ در اولین فرصت پاسخ می‌دهیم.",
        EN: "Write your message, idea or complaint; we will answer as soon as we can.",
    },
    "contact.name": {FA: "نام", EN: "Name"},
    "contact.contact": {FA: "شماره موبایل یا ایمیل", EN: "Mobile number or e-mail"},
    "contact.contact_hint": {
        FA: "برای پاسخ دادن به شما.",
        EN: "So that we can answer you.",
    },
    "contact.body": {FA: "پیام", EN: "Message"},
    "contact.submit": {FA: "ارسال پیام", EN: "Send message"},
    "contact.sent": {
        FA: "پیام شما ارسال شد. ممنون که نوشتید.",
        EN: "Your message was sent. Thank you for writing.",
    },
    "contact.error.contact": {
        FA: "یک شماره موبایل یا ایمیل معتبر بنویسید.",
        EN: "Enter a valid mobile number or e-mail address.",
    },
    "contact.error.body": {
        FA: "پیام را بنویسید (۵ تا ۲۰۰۰ نویسه).",
        EN: "Write your message (5 to 2000 characters).",
    },
}
