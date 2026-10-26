"""The language of the current request, and its translator.

Both are worked out once per request and kept on the request itself (not on
`flask.g`, which tests can share between requests). Public pages carry the
language in the URL (/fa/..., /en/...); every other page, and the error
pages, fall back to the first path segment or to the default language.
"""

from flask import current_app, request
from sqlalchemy.exc import SQLAlchemyError

from restaurant.extensions import db
from restaurant.service_factory import make_language_service, make_translation_service
from restaurant.services import FALLBACK_LANGUAGE, LanguageInfo, Translator

_CACHE_KEY = "restaurant.request_cache"


def request_cache() -> dict:
    """Return a dict that lives exactly as long as the current request."""
    return request.environ.setdefault(_CACHE_KEY, {})


def reset_session_after_error() -> None:
    """Roll back so the session is usable again after a database error."""
    db.session.rollback()


def find_available_language(code: str) -> LanguageInfo | None:
    """Return the language for `code` if visitors may use it.

    A broken or unmigrated database must not break pages: Persian stays
    available through the built-in fallback.
    """
    try:
        return make_language_service().get_available_language(code)
    except SQLAlchemyError:
        current_app.logger.exception("Could not read languages; using Persian")
        reset_session_after_error()
        return FALLBACK_LANGUAGE if code == FALLBACK_LANGUAGE.code else None


def find_default_language() -> LanguageInfo:
    """Return the default language, or Persian when the database cannot be read."""
    try:
        return make_language_service().get_default_language()
    except SQLAlchemyError:
        current_app.logger.exception("Could not read languages; using Persian")
        reset_session_after_error()
        return FALLBACK_LANGUAGE


def get_active_language() -> LanguageInfo:
    """Return the language of this request (cached for the request)."""
    cache = request_cache()
    if "language" not in cache:
        first_segment = request.path.strip("/").split("/")[0]
        cache["language"] = find_available_language(first_segment) or find_default_language()
    return cache["language"]


def set_active_language(language: LanguageInfo) -> None:
    """Record the language chosen by the URL prefix for the rest of the request."""
    request_cache()["language"] = language


def get_translator() -> Translator:
    """Return the translator for this request's language (cached for the request)."""
    cache = request_cache()
    if "translator" not in cache:
        language = get_active_language()
        try:
            cache["translator"] = make_translation_service().build_translator(language.code)
        except SQLAlchemyError:
            current_app.logger.exception("Could not read interface texts; using the defaults")
            reset_session_after_error()
            cache["translator"] = Translator(language.code)
    return cache["translator"]
