"""Access checks for admin routes: sign-in, permission levels and the safe `next` address."""

from collections.abc import Callable
from functools import wraps
from typing import Any
from urllib.parse import urlsplit

from flask import abort
from flask_login import current_user

from restaurant.admin_sections import ADMIN_SECTIONS, AdminSection
from restaurant.constants import AccessLevel, PermissionKey
from restaurant.extensions import login_manager
from restaurant.language_context import request_cache
from restaurant.models import User
from restaurant.service_factory import make_access_service, make_auth_service
from restaurant.services import NO_ACCESS, AccessProfile

PROFILE_CACHE_KEY = "admin_access_profile"
ADMIN_PATH_PREFIX = "/admin"


@login_manager.user_loader
def load_signed_in_user(user_id: str) -> User | None:
    """Find the user stored in the session; a blocked or deleted user counts as signed out."""
    if not user_id.isdecimal():
        return None
    user = make_auth_service().get_user(int(user_id))
    return user if user is not None and user.is_active else None


def current_profile() -> AccessProfile:
    """Return the access profile of the signed-in user (cached for the request)."""
    cache = request_cache()
    if PROFILE_CACHE_KEY not in cache:
        cache[PROFILE_CACHE_KEY] = (
            make_access_service().build_profile(current_user)
            if current_user.is_authenticated
            else NO_ACCESS
        )
    return cache[PROFILE_CACHE_KEY]


def permission_required(
    key: PermissionKey, required: AccessLevel = AccessLevel.VIEW
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Allow a view only for signed-in staff whose level on `key` reaches `required`.

    Visitors who are not signed in are sent to the sign-in page; signed-in staff
    without the level get a 403 page. Use `AccessLevel.EDIT` on every route that changes data.
    """

    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def guarded(*args: Any, **kwargs: Any) -> Any:
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if not current_profile().allows(key, required):
                abort(403)
            return view(*args, **kwargs)

        return guarded

    return decorator


def first_allowed_section(profile: AccessProfile) -> AdminSection | None:
    """Return the first sidebar section the profile may open, or None."""
    return next((s for s in ADMIN_SECTIONS if profile.allows(s.permission)), None)


def is_safe_admin_path(target: str | None) -> bool:
    """Return True for a local address inside the panel (blocks open redirects)."""
    if not target:
        return False
    parts = urlsplit(target)
    return (
        not parts.scheme
        and not parts.netloc
        and parts.path.startswith(f"{ADMIN_PATH_PREFIX}/")
        and not parts.path.startswith("//")
    )
