"""The accent colour: turns one chosen colour into the few CSS values that depend on it."""

DARK_TEXT = "#1a120a"
LIGHT_TEXT = "#ffffff"
SOFT_ALPHA_PERCENT = 15
CONTRAST_TARGET = 4.5


def _channel(value: int) -> float:
    """Return one colour channel (0-255) in linear light, as the contrast formula wants."""
    share = value / 255
    return share / 12.92 if share <= 0.03928 else ((share + 0.055) / 1.055) ** 2.4


def _luminance(red: int, green: int, blue: int) -> float:
    """Return the relative luminance of a colour (0 black, 1 white)."""
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def contrast_ratio(first: tuple[int, int, int], second: tuple[int, int, int]) -> float:
    """Return the contrast ratio of two colours (1 is none, 21 is black on white)."""
    lighter, darker = sorted((_luminance(*first), _luminance(*second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _rgb(hex_color: str) -> tuple[int, int, int]:
    """Split "#rrggbb" into three whole numbers."""
    return int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)


def text_color_on(hex_color: str) -> str:
    """Return the text colour that reads best on a button of this colour."""
    background = _rgb(hex_color)
    dark, light = _rgb(DARK_TEXT), _rgb(LIGHT_TEXT)
    return (
        DARK_TEXT
        if contrast_ratio(background, dark) >= contrast_ratio(background, light)
        else LIGHT_TEXT
    )


def accent_css(hex_color: str | None) -> str:
    """Return the CSS that sets the accent colour, or "" for the built-in colour.

    `hex_color` must already be a validated "#rrggbb" value; it is the only thing written.
    """
    if not hex_color:
        return ""
    red, green, blue = _rgb(hex_color)
    return (
        f":root{{--color-accent:{hex_color};--color-on-accent:{text_color_on(hex_color)};"
        f"--color-accent-soft:rgb({red} {green} {blue} / {SOFT_ALPHA_PERCENT}%)}}"
    )
