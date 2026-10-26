"""The demo's three builders (pizza, sandwich, drink) as plain data.

Prices, options and colours come from the design draft's Builder board. The colours and
shapes draw the placeholder picture; real photos replace them from the admin panel.
"""

from dataclasses import dataclass

from restaurant.constants import PreviewKind, PreviewRole

Texts = tuple[str, str]  # (Persian, English)


@dataclass(frozen=True)
class DemoOption:
    """One option of a step."""

    key: str
    name: Texts
    price: int = 0
    color: str = ""
    shape: str = ""
    amount: int = 0


@dataclass(frozen=True)
class DemoStep:
    """One step of a builder."""

    key: str
    title: Texts
    options: tuple[DemoOption, ...]
    is_multiple: bool = False
    is_required: bool = True
    is_base: bool = False
    is_layered: bool = False
    role: PreviewRole = PreviewRole.NONE


@dataclass(frozen=True)
class DemoBuilder:
    """A builder with its names, hint and steps."""

    key: str
    name: Texts
    hint: Texts
    kind: PreviewKind
    steps: tuple[DemoStep, ...]


PIZZA = DemoBuilder(
    key="pizza",
    name=("پیتزای دلخواه", "Custom pizza"),
    hint=(
        "اندازه، خمیر، سس، پنیر و مخلفات را خودتان انتخاب کنید.",
        "Pick the size, crust, sauce, cheese and toppings yourself.",
    ),
    kind=PreviewKind.PIZZA,
    steps=(
        DemoStep(
            "size",
            ("اندازه", "Size"),
            is_base=True,
            options=(
                DemoOption("small", ("کوچک (۲۵ سانتی‌متر)", "Small (25 cm)"), 160_000),
                DemoOption("medium", ("متوسط (۳۰ سانتی‌متر)", "Medium (30 cm)"), 220_000),
                DemoOption("large", ("بزرگ (۳۵ سانتی‌متر)", "Large (35 cm)"), 280_000),
            ),
        ),
        DemoStep(
            "crust",
            ("خمیر", "Crust"),
            role=PreviewRole.CRUST,
            options=(
                DemoOption("thin", ("نازک", "Thin"), 0, "#C98B3E", "thin"),
                DemoOption("thick", ("ضخیم", "Thick"), 0, "#C98B3E", "thick"),
                DemoOption(
                    "stuffed", ("لبه‌پنیری", "Cheese-stuffed"), 30_000, "#D9A441", "stuffed"
                ),
            ),
        ),
        DemoStep(
            "sauce",
            ("سس", "Sauce"),
            role=PreviewRole.SAUCE,
            options=(
                DemoOption("tomato", ("گوجه‌ای", "Tomato"), 0, "#C8391E"),
                DemoOption("white", ("سس سفید", "White sauce"), 10_000, "#F1E3C6"),
                DemoOption("pesto", ("پستو", "Pesto"), 20_000, "#5F8A3A"),
                DemoOption("bbq", ("باربیکیو", "Barbecue"), 15_000, "#6B2E17"),
            ),
        ),
        DemoStep(
            "cheese",
            ("پنیر", "Cheese"),
            role=PreviewRole.CHEESE,
            options=(
                DemoOption("mozzarella", ("موزارلا", "Mozzarella"), 0, "#E2AE48"),
                DemoOption("double", ("دوبل موزارلا", "Double mozzarella"), 35_000, "#D9962F"),
                DemoOption(
                    "mixed", ("موزارلا و چدار", "Mozzarella and cheddar"), 25_000, "#D88A2A"
                ),
            ),
        ),
        DemoStep(
            "toppings",
            ("مخلفات", "Toppings"),
            is_multiple=True,
            is_required=False,
            role=PreviewRole.TOPPING,
            options=(
                DemoOption("pepperoni", ("پپرونی", "Pepperoni"), 45_000, "#B8321F", "round", 11),
                DemoOption("mushroom", ("قارچ", "Mushroom"), 25_000, "#D9C7A3", "round", 9),
                DemoOption("ham", ("ژامبون", "Ham"), 35_000, "#E8A6A0", "square", 9),
                DemoOption("chicken", ("مرغ", "Chicken"), 45_000, "#E3BE86", "pebble", 9),
                DemoOption("pepper", ("فلفل دلمه", "Bell pepper"), 20_000, "#4F9A3C", "ring", 8),
                DemoOption("olive", ("زیتون", "Olives"), 20_000, "#2A2A2A", "ring", 6),
                DemoOption("corn", ("ذرت", "Sweet corn"), 15_000, "#F2C531", "round", 4),
                DemoOption("onion", ("پیاز", "Onion"), 10_000, "#E9DDEA", "ring", 9),
            ),
        ),
    ),
)

SANDWICH = DemoBuilder(
    key="sandwich",
    name=("ساندویچ دلخواه", "Custom sandwich"),
    hint=(
        "نان و مواد را انتخاب کنید و ترتیب لایه‌ها را خودتان بچینید.",
        "Choose the bread and fillings, then arrange the layers yourself.",
    ),
    kind=PreviewKind.SANDWICH,
    steps=(
        DemoStep(
            "bread",
            ("نان", "Bread"),
            is_base=True,
            role=PreviewRole.BREAD,
            options=(
                DemoOption("baguette", ("باگت", "Baguette"), 60_000, "#D9A35B", "bag", 54),
                DemoOption("bun", ("نان همبرگر", "Burger bun"), 55_000, "#D99A4E", "bun", 72),
                DemoOption("toast", ("نان تست", "Toast"), 50_000, "#EBD3A0", "flat", 34),
                DemoOption("lavash", ("لواش", "Lavash"), 50_000, "#E9D8B6", "flat", 18),
            ),
        ),
        DemoStep(
            "protein",
            ("مواد اصلی", "Main fillings"),
            is_multiple=True,
            is_required=False,
            is_layered=True,
            role=PreviewRole.LAYER,
            options=(
                DemoOption("cold-cut", ("کالباس", "Cold cuts"), 50_000, "#E49A93", "flat", 16),
                DemoOption(
                    "chicken", ("مرغ گریل", "Grilled chicken"), 80_000, "#E6BC83", "flat", 24
                ),
                DemoOption("koobideh", ("کوبیده", "Koobideh"), 90_000, "#8A4B2D", "flat", 26),
                DemoOption("beef-ham", ("ژامبون گوشت", "Beef ham"), 70_000, "#D98580", "flat", 16),
                DemoOption("falafel", ("فلافل", "Falafel"), 45_000, "#A4742F", "flat", 24),
            ),
        ),
        DemoStep(
            "cheese",
            ("پنیر", "Cheese"),
            is_multiple=True,
            is_required=False,
            is_layered=True,
            role=PreviewRole.LAYER,
            options=(
                DemoOption(
                    "pizza-cheese", ("پنیر پیتزا", "Pizza cheese"), 20_000, "#F4D55A", "flat", 9
                ),
                DemoOption("cheddar", ("چدار", "Cheddar"), 20_000, "#F0A93A", "flat", 9),
            ),
        ),
        DemoStep(
            "vegetables",
            ("سبزیجات", "Vegetables"),
            is_multiple=True,
            is_required=False,
            is_layered=True,
            role=PreviewRole.LAYER,
            options=(
                DemoOption("lettuce", ("کاهو", "Lettuce"), 0, "#6FAE3F", "wavy", 12),
                DemoOption("tomato", ("گوجه", "Tomato"), 0, "#D9432E", "flat", 11),
                DemoOption("pickle", ("خیارشور", "Pickles"), 0, "#8DA33C", "flat", 9),
                DemoOption("onion", ("پیاز", "Onion"), 0, "#EEE2F0", "flat", 8),
                DemoOption("mushroom", ("قارچ", "Mushroom"), 15_000, "#CDBB9C", "flat", 11),
                DemoOption("corn", ("ذرت", "Sweet corn"), 10_000, "#F2C531", "flat", 9),
            ),
        ),
        DemoStep(
            "sauces",
            ("سس", "Sauces"),
            is_multiple=True,
            is_required=False,
            is_layered=True,
            role=PreviewRole.LAYER,
            options=(
                DemoOption("mayo", ("مایونز", "Mayonnaise"), 0, "#F6F0DD", "sauce", 6),
                DemoOption("ketchup", ("کچاپ", "Ketchup"), 0, "#C23A24", "sauce", 6),
                DemoOption("mustard", ("خردل", "Mustard"), 0, "#E0B91F", "sauce", 6),
                DemoOption("special", ("سس مخصوص", "House sauce"), 10_000, "#E48B4A", "sauce", 6),
                DemoOption("hot", ("سس تند", "Hot sauce"), 5_000, "#B02818", "sauce", 6),
            ),
        ),
    ),
)

DRINK = DemoBuilder(
    key="drink",
    name=("نوشیدنی دلخواه", "Custom drink"),
    hint=(
        "نوع نوشیدنی، اندازه، طعم و افزودنی را انتخاب کنید.",
        "Choose the drink, size, flavours and extras.",
    ),
    kind=PreviewKind.DRINK,
    steps=(
        DemoStep(
            "type",
            ("نوع نوشیدنی", "Drink"),
            is_base=True,
            role=PreviewRole.BASE,
            options=(
                DemoOption("lemonade", ("لیموناد", "Lemonade"), 70_000, "#E8D96B"),
                DemoOption("smoothie", ("اسموتی میوه", "Fruit smoothie"), 100_000, "#E9677F"),
                DemoOption("milkshake", ("میلک‌شیک", "Milkshake"), 110_000, "#F0D8C0"),
                DemoOption("iced-coffee", ("قهوه سرد", "Iced coffee"), 90_000, "#7A4A2E"),
            ),
        ),
        DemoStep(
            "size",
            ("اندازه", "Size"),
            role=PreviewRole.SIZE,
            options=(
                DemoOption("small", ("کوچک (۳۰۰ میلی‌لیتر)", "Small (300 ml)"), 0, "", "", 58),
                DemoOption(
                    "medium", ("متوسط (۴۰۰ میلی‌لیتر)", "Medium (400 ml)"), 15_000, "", "", 70
                ),
                DemoOption("large", ("بزرگ (۵۰۰ میلی‌لیتر)", "Large (500 ml)"), 30_000, "", "", 82),
            ),
        ),
        DemoStep(
            "flavors",
            ("طعم‌ها", "Flavours"),
            is_multiple=True,
            is_required=False,
            role=PreviewRole.FLAVOR,
            options=(
                DemoOption("strawberry", ("توت‌فرنگی", "Strawberry"), 15_000, "#E04668"),
                DemoOption("mango", ("انبه", "Mango"), 20_000, "#F3A91C"),
                DemoOption("banana", ("موز", "Banana"), 15_000, "#F2E08A"),
                DemoOption("mint", ("نعناع", "Mint"), 5_000, "#6FC28A"),
                DemoOption("passion", ("پشن‌فروت", "Passion fruit"), 20_000, "#F08C2E"),
                DemoOption("chocolate", ("شکلات", "Chocolate"), 15_000, "#5B3A2A"),
            ),
        ),
        DemoStep(
            "extras",
            ("افزودنی‌ها", "Extras"),
            is_multiple=True,
            is_required=False,
            role=PreviewRole.EXTRA,
            options=(
                DemoOption("ice", ("یخ اضافه", "Extra ice"), 0, "#DDEFF6", "ice"),
                DemoOption("cream", ("خامه", "Whipped cream"), 10_000, "#FBF4E4", "cream"),
                DemoOption("honey", ("عسل", "Honey"), 10_000, "#E0A93A", "other"),
            ),
        ),
        DemoStep(
            "sweetness",
            ("شیرینی", "Sweetness"),
            options=(
                DemoOption("none", ("بدون شکر", "No sugar")),
                DemoOption("low", ("کم", "Low")),
                DemoOption("medium", ("متوسط", "Medium")),
                DemoOption("high", ("زیاد", "High")),
            ),
        ),
    ),
)

DEMO_BUILDERS = (PIZZA, SANDWICH, DRINK)
