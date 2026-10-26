"""Web helpers of the customer area: the sign-in guard, safe return addresses, form errors."""

from collections.abc import Callable
from functools import wraps
from typing import Any
from urllib.parse import urlsplit

from flask import redirect, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm

from restaurant.language_context import get_translator
from restaurant.services import ProfileProblem, RegistrationProblem

PENDING_SESSION_KEY = "pending_registration_user_id"
PAGE_SIZE = 10

REGISTRATION_ERRORS: dict[RegistrationProblem, tuple[str, str]] = {
    RegistrationProblem.BAD_NAME: ("customer_name", "account.error.name"),
    RegistrationProblem.BAD_PHONE: ("phone", "account.error.phone"),
    RegistrationProblem.BAD_EMAIL: ("email", "account.error.email"),
    RegistrationProblem.WEAK_PASSWORD: ("password", "account.error.password_short"),
    RegistrationProblem.PHONE_TAKEN: ("phone", "account.register.error.phone_taken"),
    RegistrationProblem.EMAIL_TAKEN: ("email", "account.register.error.email_taken"),
}
PROFILE_ERRORS: dict[ProfileProblem, tuple[str, str]] = {
    ProfileProblem.BAD_NAME: ("customer_name", "account.error.name"),
    ProfileProblem.BAD_EMAIL: ("email", "account.error.email"),
    ProfileProblem.EMAIL_TAKEN: ("email", "account.profile.error.email_taken"),
    ProfileProblem.WRONG_PASSWORD: ("current_password", "account.password.error.wrong"),
    ProfileProblem.WEAK_PASSWORD: ("new_password", "account.error.password_short"),
}
ADDRESS_ERRORS: dict[ProfileProblem, tuple[str, str]] = {
    ProfileProblem.EMPTY_ADDRESS: ("text", "account.error.address"),
    ProfileProblem.ADDRESS_TOO_LONG: ("text", "account.error.address"),
    ProfileProblem.TOO_MANY_ADDRESSES: ("text", "account.addresses.error.too_many"),
}


def add_form_error(form: FlaskForm, field_name: str, text_key: str) -> None:
    """Show a message (looked up in the page language) under one field of a form."""
    field = getattr(form, field_name)
    field.errors = [*field.errors, get_translator()(text_key)]


def safe_return_path(target: str | None) -> str | None:
    """Return `target` when it is an address on this site, else None (blocks open redirects)."""
    if not target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not target.startswith("/") or target.startswith("//"):
        return None
    return target


def sign_in_url_for_current_page() -> str:
    """Return the sign-in address that brings the visitor back to the page they asked for."""
    return url_for("public.login", next=request.full_path.rstrip("?"))


def customer_required(view: Callable[..., Any]) -> Callable[..., Any]:
    """Send visitors who are not signed in to the sign-in page, then back to this page."""

    @wraps(view)
    def guarded(*args: Any, **kwargs: Any) -> Any:
        if not current_user.is_authenticated:
            return redirect(sign_in_url_for_current_page())
        return view(*args, **kwargs)

    return guarded
