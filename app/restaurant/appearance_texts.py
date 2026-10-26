"""Interface texts of the admin "Site appearance" section."""

from restaurant.constants import LANGUAGE_CODE_ENGLISH as EN
from restaurant.constants import LANGUAGE_CODE_PERSIAN as FA

_BACKGROUNDS = {
    "home-hero": ("صفحه‌ی اصلی · بالای صفحه", "Home · top of the page"),
    "home-showcase": ("صفحه‌ی اصلی · قاب ویدیو", "Home · framed video"),
    "home-modes": ("صفحه‌ی اصلی · روش‌های سفارش", "Home · ways to order"),
    "home-dishes": ("صفحه‌ی اصلی · غذاهای پیشنهادی", "Home · chef's picks"),
    "home-how": ("صفحه‌ی اصلی · چطور کار می‌کند", "Home · how it works"),
    "home-reserve": ("صفحه‌ی اصلی · رزرو میز", "Home · table booking"),
    "home-footer": ("صفحه‌ی اصلی · پایین صفحه", "Home · footer"),
    "menu-page": ("صفحه‌ی منو", "Menu page"),
    "builder-page": ("صفحه‌ی ساخت غذا", "Build-your-own page"),
    "reserve-page": ("صفحه‌ی رزرو میز", "Table booking page"),
}

_SECTIONS = {
    "top": ("بالای صفحه (ثابت)", "Top of the page (fixed)"),
    "modes": ("روش‌های سفارش", "Ways to order"),
    "dishes": ("غذاهای پیشنهادی", "Chef's picks"),
    "how": ("چطور کار می‌کند", "How it works"),
    "reserve": ("رزرو میز", "Table booking"),
    "contact": ("پایین صفحه و تماس (ثابت)", "Footer and contact (fixed)"),
}

SITE_TEXTS: dict[str, dict[str, str]] = {
    "admin.nav.site": {FA: "ظاهر سایت", EN: "Site appearance"},
    "admin.site.tab_general": {FA: "عمومی", EN: "General"},
    "admin.site.tab_backgrounds": {FA: "پس‌زمینه‌ها", EN: "Backgrounds"},
    "admin.site.tab_home": {FA: "صفحه‌ی اصلی", EN: "Home page"},
    # General
    "admin.site.brand": {FA: "نام رستوران", EN: "Restaurant name"},
    "admin.site.brand_name": {FA: "نام نمایش‌داده‌شده", EN: "Name shown on the site"},
    "admin.site.accent": {FA: "رنگ اصلی", EN: "Accent colour"},
    "admin.site.accent_hint": {
        FA: "رنگ دکمه‌ها و تأکیدها؛ رنگ نوشته‌ی روی آن خودکار انتخاب می‌شود تا خوانا بماند.",
        EN: (
            "Used for buttons and highlights; the text on top is picked "
            "automatically to stay readable."
        ),
    },
    "admin.site.accent_color": {FA: "رنگ", EN: "Colour"},
    "admin.site.default_color": {FA: "از رنگ پیش‌فرض استفاده کن", EN: "Use the default colour"},
    "admin.site.logo": {FA: "لوگو", EN: "Logo"},
    "admin.site.logo_hint": {
        FA: "کنار نام در بالای صفحه نمایش داده می‌شود. تصویر PNG، JPG یا WebP؛ حداکثر ۵ مگابایت.",
        EN: "Shown beside the name at the top of the page. PNG, JPG or WebP, 5 MB at most.",
    },
    "admin.site.logo_upload": {FA: "لوگوی تازه", EN: "New logo"},
    "admin.site.remove_logo": {FA: "لوگو را بردار", EN: "Remove the logo"},
    "admin.site.error.brand_name": {
        FA: "نام باید بین ۱ تا ۶۰ نویسه باشد.",
        EN: "The name must be 1 to 60 characters long.",
    },
    "admin.site.error.accent_color": {
        FA: "رنگ باید به شکل #RRGGBB باشد.",
        EN: "The colour must look like #RRGGBB.",
    },
    # Backgrounds
    "admin.site.backgrounds_hint": {
        FA: (
            "هر پس‌زمینه ویدیو و پوستر دارد. اگر ویدیو نباشد پوستر و اگر پوستر هم "
            "نباشد یک گرادیان تیره نمایش داده می‌شود."
        ),
        EN: (
            "Each background has a video and a poster. Without a video the poster "
            "shows, and without both a dark gradient."
        ),
    },
    "admin.site.dim": {FA: "تیرگی روی ویدیو (٪)", EN: "Darkening over the video (%)"},
    "admin.site.mobile_mode": {FA: "روی موبایل", EN: "On phones"},
    "admin.site.mode.poster_only": {FA: "فقط پوستر (سبک‌تر)", EN: "Poster only (lighter)"},
    "admin.site.mode.video": {FA: "ویدیو هم پخش شود", EN: "Play the video too"},
    "admin.site.enabled": {FA: "نمایش داده شود", EN: "Show this background"},
    "admin.site.poster": {FA: "پوستر (تصویر)", EN: "Poster (image)"},
    "admin.site.video": {FA: "ویدیو (MP4)", EN: "Video (MP4)"},
    "admin.site.video_hint": {
        FA: "کوتاه، بی‌صدا و فشرده؛ حداکثر ۱۲ مگابایت.",
        EN: "Short, silent and compressed; 12 MB at most.",
    },
    "admin.site.remove_poster": {FA: "پوستر را بردار", EN: "Remove the poster"},
    "admin.site.remove_video": {FA: "ویدیو را بردار", EN: "Remove the video"},
    "admin.site.no_poster": {FA: "بدون پوستر", EN: "No poster"},
    "admin.site.no_video": {FA: "بدون ویدیو", EN: "No video"},
    "admin.site.preview_video": {FA: "دیدن ویدیو", EN: "Watch the video"},
    "admin.site.error.dim": {
        FA: "تیرگی باید عددی بین ۰ و ۱۰۰ باشد.",
        EN: "The darkening must be a number between 0 and 100.",
    },
    "admin.site.video.error.empty": {FA: "فایل خالی است.", EN: "The file is empty."},
    "admin.site.video.error.too_large": {
        FA: "ویدیو بزرگ‌تر از ۱۲ مگابایت است.",
        EN: "The video is larger than 12 MB.",
    },
    "admin.site.video.error.not_a_video": {
        FA: "فایل باید ویدیوی MP4 باشد.",
        EN: "The file must be an MP4 video.",
    },
    # Home page
    "admin.site.sections": {FA: "ترتیب بخش‌های صفحه‌ی اصلی", EN: "Home page section order"},
    "admin.site.sections_hint": {
        FA: (
            "با فلش‌ها جابه‌جا کنید و بخش‌هایی را که نمی‌خواهید خاموش کنید. بالا و "
            "پایین صفحه ثابت‌اند."
        ),
        EN: (
            "Move sections with the arrows and untick the ones you do not want. The "
            "top and the bottom stay fixed."
        ),
    },
    "admin.site.fixed": {FA: "ثابت", EN: "Fixed"},
    "admin.site.move_up": {FA: "یک جا بالاتر", EN: "Move up"},
    "admin.site.move_down": {FA: "یک جا پایین‌تر", EN: "Move down"},
    "admin.site.home_texts": {FA: "متن‌های صفحه‌ی اصلی", EN: "Home page texts"},
    "admin.site.home_texts_hint": {
        FA: "متن‌های دیگر سایت را از بخش «زبان‌ها» ویرایش کنید.",
        EN: "Edit the other texts of the site in the Languages section.",
    },
}
for _key, (_fa, _en) in _BACKGROUNDS.items():
    SITE_TEXTS[f"admin.site.bg.{_key}"] = {FA: _fa, EN: _en}
for _key, (_fa, _en) in _SECTIONS.items():
    SITE_TEXTS[f"admin.site.section.{_key}"] = {FA: _fa, EN: _en}
