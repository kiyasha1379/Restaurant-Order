"""Public site pages, all under a language prefix (/fa/..., /en/...)."""

from flask import Blueprint

from restaurant.blueprints.language_routing import LANGUAGE_PARAMETER, attach_language_routing

public_blueprint = Blueprint("public", __name__, url_prefix=f"/<{LANGUAGE_PARAMETER}>")
attach_language_routing(public_blueprint)

from restaurant.blueprints.public import routes  # noqa: E402,F401  (registers the routes)
