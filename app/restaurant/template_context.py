"""Values every template can use: language, translator, brand name, demo flag, switcher."""

from typing import Any

from flask import Flask, current_app, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from restaurant.cart_web import count_cart_items
from restaurant.constants import DEFAULT_BRAND_NAME
from restaurant.language_context import (
    get_active_language,
    get_translator,
    reset_session_after_error,
)
from restaurant.navigation import has_page, is_current_page, list_navigation_items
from restaurant.service_factory import (
    make_background_service,
    make_language_service,
    make_site_settings_service,
)
from restaurant.services import FALLBACK_LANGUAGE, BackgroundView, LanguageInfo


def build_language_switch_links() -> list[dict[str, str]]:
    """Links to the current page in every other available language.

    Empty when only one language is on, so the switcher disappears.
    """
    active = get_active_language()
    try:
        languages = make_language_service().list_available_languages()
    except SQLAlchemyError:
        current_app.logger.exception("Could not read languages for the switcher")
        reset_session_after_error()
        languages = [FALLBACK_LANGUAGE]
    if len(languages) < 2:
        return []
    return [
        {"code": language.code, "name": language.name, "url": _switch_url(language)}
        for language in languages
        if language.code != active.code
    ]


def _switch_url(language: LanguageInfo) -> str:
    """Build the address of the current page in `language`.

    Pages that live under a language prefix keep their other path parts and
    query string; any other page (an error page, say) links to the home page.
    """
    endpoint = request.endpoint
    has_language_prefix = (
        endpoint is not None
        and request.view_args is not None
        and current_app.url_map.is_endpoint_expecting(endpoint, "lang_code")
    )
    if not has_language_prefix:
        return url_for("public.home", lang_code=language.code)
    view_args = {**request.view_args, "lang_code": language.code}
    return url_for(endpoint, **view_args, **request.args.to_dict(flat=True))


def find_background(key: str) -> BackgroundView | None:
    """Return the background for `key`, or None so the page draws its gradient instead.

    A broken database must not break a page that only wants a backdrop.
    """
    try:
        return make_background_service().find(key)
    except SQLAlchemyError:
        current_app.logger.exception("Could not read background %s", key)
        reset_session_after_error()
        return None


SCRIPT_TEXT_KEYS = (
    "cart.empty",
    "cart.increase",
    "cart.decrease",
    "cart.remove",
    "cart.error",
    "cart.added",
    "cart.removed_unavailable",
    "cart.item_count",
    "cart.item_count_one",
    "cart.view",
    "price.currency",
    "checkout.error.choice",
    "builder.free",
    "builder.layers.top",
    "builder.layers.bottom",
    "builder.layers.fixed",
    "builder.layers.up",
    "builder.layers.down",
    "builder.layers.empty",
    "builder.summary.none",
    "builder.missing_step",
    "builder.error.unknown",
    "builder.error.unavailable",
    "builder.error.too_many",
    "builder.error.missing",
)


def build_site_config() -> dict[str, Any]:
    """Collect what the page scripts need: language, API addresses and a few texts.

    It is written into the page as JSON, so scripts never guess addresses or hard-code texts.
    """
    language = get_active_language()
    translate = get_translator()
    return {
        "language": language.code,
        "locale": "fa-IR" if language.code == "fa" else "en-US",
        "urls": {
            "cart": url_for("api.get_cart"),
            "cartAdd": url_for("api.add_to_cart"),
            "cartUpdate": url_for("api.update_cart"),
            "quote": url_for("api.quote"),
            "cartAddCustom": url_for("api.add_custom_to_cart"),
            "buildQuote": url_for("api.build_quote", key="KEY"),
            "orderStatus": url_for("api.order_status", public_token="TOKEN"),
            "orderStream": url_for("api.order_stream", public_token="TOKEN"),
            "cartPage": url_for("public.cart"),
        },
        "texts": {key: translate(key) for key in SCRIPT_TEXT_KEYS},
    }


def build_template_context() -> dict[str, Any]:
    """Collect the shared template values for one render.

    Error pages are rendered through this too, so a broken or missing
    database must never break them: on a database error we log it and fall
    back to Persian, the default texts and the default brand name.
    """
    try:
        brand_name = make_site_settings_service().get_brand_name()
    except SQLAlchemyError:
        current_app.logger.exception("Could not read settings; using the default brand name")
        reset_session_after_error()
        brand_name = DEFAULT_BRAND_NAME

    return {
        "language": get_active_language(),
        "t": get_translator(),
        "brand_name": brand_name,
        "demo_mode": current_app.config["DEMO_MODE"],
        "language_switch_links": build_language_switch_links,
        "find_background": find_background,
        "navigation_items": list_navigation_items,
        "is_current_page": is_current_page,
        "has_page": has_page,
        "site_config": build_site_config,
        "cart_count": count_cart_items(),
    }


def register_template_context(app: Flask) -> None:
    """Make the shared values available in every template."""
    app.context_processor(build_template_context)
