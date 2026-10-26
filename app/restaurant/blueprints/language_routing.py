"""Language-prefixed addresses: /fa/..., /en/...

Every public route lives under `/<lang_code>`. This module keeps that rule in
one place: it checks the prefix, redirects when a language is switched off,
fills `lang_code` in automatically when templates call `url_for`, and sends
the bare address `/` to the default language.
"""

from flask import (
    Blueprint,
    Flask,
    abort,
    current_app,
    has_request_context,
    redirect,
    request,
    url_for,
)
from werkzeug.wrappers import Response

from restaurant.language_context import (
    find_available_language,
    find_default_language,
    get_active_language,
    request_cache,
    set_active_language,
)
from restaurant.service_factory import make_language_service

LANGUAGE_PARAMETER = "lang_code"
REQUESTED_CODE_KEY = "requested_language_code"

root_blueprint = Blueprint("root", __name__)


@root_blueprint.get("/")
def index() -> Response:
    """Send visitors of the bare address to the default language's home page."""
    return redirect(url_for("public.home", lang_code=find_default_language().code))


def _store_language_code(endpoint: str | None, values: dict | None) -> None:
    """Take `lang_code` out of the URL values and remember it for the request."""
    if values and LANGUAGE_PARAMETER in values:
        request_cache()[REQUESTED_CODE_KEY] = values.pop(LANGUAGE_PARAMETER)


def _check_language_code() -> Response | None:
    """Show the page, redirect to the default language, or answer 404 for an unknown code."""
    code = request_cache().get(REQUESTED_CODE_KEY)
    if code is None:
        return None
    available_language = find_available_language(code)
    if available_language is not None:
        set_active_language(available_language)
        return None
    if not make_language_service().is_supported_code(code):
        abort(404)
    return redirect(_url_in_language(find_default_language().code))


def _url_in_language(language_code: str) -> str:
    """Return the current address with the language prefix replaced."""
    view_args = {**(request.view_args or {}), LANGUAGE_PARAMETER: language_code}
    return url_for(request.endpoint, **view_args, **request.args.to_dict(flat=True))


def _add_language_code(endpoint: str, values: dict) -> None:
    """Fill `lang_code` into `url_for` calls so templates never write it by hand."""
    if LANGUAGE_PARAMETER in values or not has_request_context():
        return
    if current_app.url_map.is_endpoint_expecting(endpoint, LANGUAGE_PARAMETER):
        values[LANGUAGE_PARAMETER] = get_active_language().code


def attach_language_routing(blueprint: Blueprint) -> None:
    """Make `blueprint` read and check the language prefix of its routes."""
    blueprint.url_value_preprocessor(_store_language_code)
    blueprint.before_request(_check_language_code)


def register_language_routing(app: Flask) -> None:
    """Register the root redirect and the automatic `lang_code` filling."""
    app.register_blueprint(root_blueprint)
    app.url_defaults(_add_language_code)
