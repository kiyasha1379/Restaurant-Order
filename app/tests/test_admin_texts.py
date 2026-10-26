"""Every interface text the admin code asks for must exist in both languages."""

import re
from pathlib import Path

from restaurant.default_texts import DEFAULT_TEXTS

PACKAGE = Path(__file__).resolve().parents[1] / "restaurant"
TEMPLATE_KEY = re.compile(r"""\bt\(\s*["']([a-z0-9_.]+)["']""")
# Text keys have three or more parts; endpoints such as "admin.menu" have two.
PYTHON_KEY = re.compile(r"""["'](admin\.[a-z0-9_]+\.[a-z0-9_.]+)["']""")
SAVED_KEY = re.compile(r"""translate\(\s*["'](admin\.[a-z0-9_.]+)["']""")


def _keys_in(paths) -> set[str]:
    found = set()
    for path in paths:
        text = path.read_text(encoding="utf-8")
        found |= set(TEMPLATE_KEY.findall(text))
    return found


def test_admin_templates_only_use_known_texts() -> None:
    used = _keys_in((PACKAGE / "templates" / "admin").rglob("*.html"))
    # A key ending in "." or "_" is a prefix completed at render time ("admin.users.perm." ~ key).
    used = {key for key in used if not key.endswith((".", "_"))}
    missing = sorted(key for key in used if key not in DEFAULT_TEXTS)
    assert not missing, f"Texts used in admin templates but not defined: {missing}"


def test_admin_python_code_only_asks_for_known_texts() -> None:
    used = set()
    for path in (PACKAGE / "blueprints" / "admin").glob("*.py"):
        used |= set(PYTHON_KEY.findall(path.read_text(encoding="utf-8")))
        used |= set(SAVED_KEY.findall(path.read_text(encoding="utf-8")))
    for path in (PACKAGE / "forms").glob("admin_*.py"):
        used |= set(PYTHON_KEY.findall(path.read_text(encoding="utf-8")))
    missing = sorted(key for key in used if key not in DEFAULT_TEXTS)
    assert not missing, f"Texts asked for in admin code but not defined: {missing}"


def test_every_admin_text_has_both_languages() -> None:
    for key, values in DEFAULT_TEXTS.items():
        if key.startswith("admin."):
            assert values.get("fa") and values.get("en"), key


def test_permission_labels_exist_for_every_permission_and_level() -> None:
    from restaurant.constants import PermissionKey

    for key in PermissionKey:
        assert f"admin.users.perm.{key.value}" in DEFAULT_TEXTS
    for level in ("none", "view", "edit", "money"):
        assert f"admin.users.level.{level}" in DEFAULT_TEXTS
