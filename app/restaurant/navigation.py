"""Main navigation: which links the header and the phone tab bar show.

A link appears only when its page exists, so each phase that adds a page
(builder, reservation, account) shows up in the menus without editing templates.
"""

from dataclasses import dataclass

from flask import current_app, request


@dataclass(frozen=True)
class NavigationItem:
    """One link: the endpoint it opens, the text key for its label and its tab-bar icon."""

    endpoint: str
    text_key: str
    icon: str
    in_header: bool = True
    in_tab_bar: bool = True


NAVIGATION_ITEMS = (
    NavigationItem("public.home", "nav.home", "home"),
    NavigationItem("public.menu", "nav.menu", "menu"),
    NavigationItem("public.builder", "nav.builder", "builder"),
    NavigationItem("public.reserve", "nav.reserve", "reserve"),
    NavigationItem("public.account", "nav.account", "account", in_header=False),
)


def list_navigation_items() -> list[NavigationItem]:
    """Return the items whose page exists in this version of the app."""
    return [item for item in NAVIGATION_ITEMS if has_page(item.endpoint)]


def is_current_page(endpoint: str) -> bool:
    """Return True when the visitor is on the page this endpoint serves."""
    return request.endpoint == endpoint


def has_page(endpoint: str) -> bool:
    """Return True when this version of the app has a route for the endpoint."""
    return endpoint in current_app.view_functions
