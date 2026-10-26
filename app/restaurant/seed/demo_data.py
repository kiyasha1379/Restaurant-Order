"""The demo's sample content, as plain data (no database code here).

Texts come from the design draft. Everything is a stand-in the owner replaces
from the admin panel; the background files live in static/media/backgrounds.
"""

from dataclasses import dataclass

from restaurant.constants import MobileBackgroundMode


@dataclass(frozen=True)
class DemoBackground:
    """One row of the `backgrounds` table."""

    key: str
    video_path: str
    poster_path: str
    dim: float
    mobile_mode: MobileBackgroundMode = MobileBackgroundMode.POSTER_ONLY


@dataclass(frozen=True)
class DemoDish:
    """A dish with its Persian and English texts."""

    price: int
    name: tuple[str, str]
    description: tuple[str, str]
    ingredients: tuple[str, str]
    serving_note: tuple[str, str]
    is_chefs_pick: bool = False


@dataclass(frozen=True)
class DemoCategory:
    """A category with its names and dishes."""

    slug: str
    name: tuple[str, str]
    dishes: tuple[DemoDish, ...]


def _background(key: str, dim: float) -> DemoBackground:
    """Build a background whose files are named after its key."""
    return DemoBackground(
        key=key,
        video_path=f"media/backgrounds/{key}.mp4",
        poster_path=f"media/backgrounds/{key}.webp",
        dim=dim,
    )


DEMO_BACKGROUNDS = (
    _background("home-hero", 0.40),
    _background("home-showcase", 0.0),
    _background("home-modes", 0.30),
    _background("home-dishes", 0.38),
    _background("home-how", 0.50),
    _background("home-reserve", 0.25),
    _background("home-footer", 0.45),
    DemoBackground(
        key="builder-page",
        video_path="media/backgrounds/home-modes.mp4",
        poster_path="media/backgrounds/home-modes.webp",
        dim=0.58,
    ),
    DemoBackground(
        key="menu-page",
        video_path="media/backgrounds/home-dishes.mp4",
        poster_path="media/backgrounds/home-dishes.webp",
        dim=0.60,
    ),
)

DEMO_CATEGORIES = (
    DemoCategory(
        "kebab",
        ("کباب‌ها", "Kebabs"),
        (
            DemoDish(
                280_000,
                ("کباب کوبیده", "Koobideh Kebab"),
                (
                    "دو سیخ کوبیده‌ی گوشت، با برنج و گوجه‌ی کبابی",
                    "Two skewers of minced meat with rice and grilled tomato",
                ),
                (
                    "گوشت گوسفندی و گوساله، پیاز، برنج، گوجه",
                    "Lamb and beef, onion, rice, tomato",
                ),
                ("۲۵ دقیقه · ۱ نفر", "25 min · serves 1"),
                is_chefs_pick=True,
            ),
            DemoDish(
                240_000,
                ("جوجه‌کباب زعفرانی", "Saffron Chicken Kebab"),
                (
                    "مرغ ماریناد شده با زعفران، همراه برنج و سالاد شیرازی",
                    "Saffron-marinated chicken with rice and Shirazi salad",
                ),
                ("سینه‌ی مرغ، زعفران، لیمو، برنج", "Chicken breast, saffron, lemon, rice"),
                ("۲۵ دقیقه · ۱ نفر", "25 min · serves 1"),
                is_chefs_pick=True,
            ),
        ),
    ),
    DemoCategory(
        "stew",
        ("خورش‌ها", "Stews"),
        (
            DemoDish(
                220_000,
                ("قورمه‌سبزی", "Ghormeh Sabzi"),
                (
                    "خورش سبزی معطر با گوشت و لوبیا، همراه برنج",
                    "Fragrant herb stew with meat and beans, served with rice",
                ),
                (
                    "سبزی تازه، گوشت، لوبیا قرمز، لیمو عمانی",
                    "Fresh herbs, meat, kidney beans, dried lime",
                ),
                ("۲۰ دقیقه · ۱ نفر", "20 min · serves 1"),
                is_chefs_pick=True,
            ),
            DemoDish(
                210_000,
                ("زرشک‌پلو با مرغ", "Barberry Rice with Chicken"),
                (
                    "مرغ سرخ‌شده، زرشک و برنج زعفرانی",
                    "Pan-fried chicken, barberries and saffron rice",
                ),
                ("مرغ، زرشک، زعفران، برنج", "Chicken, barberries, saffron, rice"),
                ("۲۰ دقیقه · ۱ نفر", "20 min · serves 1"),
                is_chefs_pick=True,
            ),
            DemoDish(
                210_000,
                ("قیمه با سیب‌زمینی", "Gheymeh with Fries"),
                (
                    "خورش لپه و گوشت با سیب‌زمینی سرخ‌شده",
                    "Split-pea and meat stew with fried potato",
                ),
                ("لپه، گوشت، رب، سیب‌زمینی", "Split peas, meat, tomato paste, potato"),
                ("۲۰ دقیقه · ۱ نفر", "20 min · serves 1"),
            ),
        ),
    ),
    DemoCategory(
        "pizza",
        ("پیتزا", "Pizza"),
        (
            DemoDish(
                260_000,
                ("پیتزا مارگاریتا", "Margherita Pizza"),
                (
                    "خمیر نازک، سس گوجه، پنیر موزارلا و ریحان تازه",
                    "Thin crust, tomato sauce, mozzarella and fresh basil",
                ),
                ("خمیر، گوجه، موزارلا، ریحان", "Dough, tomato, mozzarella, basil"),
                ("۲۰ دقیقه · ۱ تا ۲ نفر", "20 min · serves 1–2"),
            ),
            DemoDish(
                310_000,
                ("پیتزا پپرونی", "Pepperoni Pizza"),
                (
                    "پپرونی ملس روی پنیر داغ و سس گوجه",
                    "Spicy pepperoni on hot cheese and tomato sauce",
                ),
                ("پپرونی، موزارلا، سس گوجه", "Pepperoni, mozzarella, tomato sauce"),
                ("۲۰ دقیقه · ۱ تا ۲ نفر", "20 min · serves 1–2"),
            ),
        ),
    ),
    DemoCategory(
        "starter",
        ("پیش‌غذاها", "Starters"),
        (
            DemoDish(
                95_000,
                ("کشک بادمجان", "Kashk-e Bademjan"),
                (
                    "بادمجان سرخ‌شده با کشک و پیازداغ",
                    "Fried aubergine with kashk and crispy onion",
                ),
                ("بادمجان، کشک، پیازداغ، نعنا", "Aubergine, kashk, fried onion, mint"),
                ("۱۰ دقیقه · ۲ نفر", "10 min · serves 2"),
            ),
            DemoDish(
                70_000,
                ("سالاد شیرازی", "Shirazi Salad"),
                ("خیار، گوجه و پیاز با آب‌لیمو", "Cucumber, tomato and onion with lime juice"),
                ("خیار، گوجه، پیاز، آب‌لیمو", "Cucumber, tomato, onion, lime juice"),
                ("۵ دقیقه · ۲ نفر", "5 min · serves 2"),
            ),
        ),
    ),
    DemoCategory(
        "drink",
        ("نوشیدنی‌ها", "Drinks"),
        (
            DemoDish(
                35_000,
                ("دوغ محلی", "Local Doogh"),
                ("دوغ خنک با نعنای خشک", "Chilled yogurt drink with dried mint"),
                ("ماست، آب، نعنای خشک", "Yogurt, water, dried mint"),
                ("آماده · ۱ لیوان", "Ready · 1 glass"),
            ),
            DemoDish(
                30_000,
                ("چای سنتی", "Traditional Tea"),
                ("چای دم‌کرده با نبات", "Brewed tea with rock candy"),
                ("چای ایرانی، نبات", "Persian tea, rock candy"),
                ("۵ دقیقه · ۱ نفر", "5 min · serves 1"),
            ),
        ),
    ),
)
