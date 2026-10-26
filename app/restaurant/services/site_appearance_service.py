"""Site appearance: backgrounds, the order of the home sections and the home page texts."""

from dataclasses import dataclass

from restaurant.constants import (
    BACKGROUND_KEYS,
    DEFAULT_HOME_SECTION_ORDER,
    MobileBackgroundMode,
)
from restaurant.models import Background
from restaurant.repositories import BackgroundRepository, SiteSectionRepository
from restaurant.services.language_admin_service import LanguageAdminService

DEFAULT_DIM = 0.45

# The home texts the owner may edit here; every other text stays in the Languages section.
HOME_TEXT_KEYS = (
    "home.kicker",
    "home.headline",
    "home.lead",
    "home.modes.title",
    "home.dishes.title",
    "home.how.title",
    "home.reserve.title",
    "home.reserve.text",
)


class SiteAppearanceError(ValueError):
    """The appearance settings were refused (an unknown key or a value out of range)."""


@dataclass(frozen=True)
class SectionRow:
    """One movable home section as the admin shows it."""

    key: str
    is_visible: bool


@dataclass(frozen=True)
class BackgroundRow:
    """One background as the admin shows it (defaults when it was never stored)."""

    key: str
    video_path: str | None
    poster_path: str | None
    dim: float
    is_enabled: bool
    mobile_mode: MobileBackgroundMode


class SiteAppearanceService:
    """Reads and changes how the public site looks."""

    def __init__(
        self,
        section_repository: SiteSectionRepository,
        background_repository: BackgroundRepository,
        language_admin: LanguageAdminService,
    ) -> None:
        """Receive the collaborators instead of importing them, so tests can swap them."""
        self._sections = section_repository
        self._backgrounds = background_repository
        self._language_admin = language_admin

    # Home sections -------------------------------------------------------------------

    def home_sections(self) -> list[SectionRow]:
        """Return every movable section in order; unstored ones follow, visible."""
        known = {key.value for key in DEFAULT_HOME_SECTION_ORDER}
        stored = [row for row in self._sections.list_ordered() if row.key in known]
        rows = [SectionRow(row.key, row.is_visible) for row in stored]
        seen = {row.key for row in rows}
        rows += [
            SectionRow(key.value, True) for key in DEFAULT_HOME_SECTION_ORDER if key not in seen
        ]
        return rows

    def visible_home_sections(self) -> list[str]:
        """Return the keys of the sections the home page draws, in order."""
        return [row.key for row in self.home_sections() if row.is_visible]

    def save_home_sections(self, order: list[str], visible: set[str]) -> None:
        """Store the order and which sections show. The caller commits.

        `order` must list every movable section exactly once. Raises SiteAppearanceError.
        """
        known = [key.value for key in DEFAULT_HOME_SECTION_ORDER]
        if sorted(order) != sorted(known) or not visible <= set(known):
            raise SiteAppearanceError("sections")
        for position, key in enumerate(order):
            self._sections.save(key, position, key in visible)

    # Backgrounds ---------------------------------------------------------------------

    def list_backgrounds(self) -> list[BackgroundRow]:
        """Return every background the site draws, in a fixed order."""
        stored = self._backgrounds.list_by_keys(BACKGROUND_KEYS)
        return [self._row(key, stored.get(key)) for key in BACKGROUND_KEYS]

    def update_background(
        self, key: str, dim: float, is_enabled: bool, mobile_mode: MobileBackgroundMode
    ) -> None:
        """Change how one background is drawn. The caller commits. Raises SiteAppearanceError."""
        if not 0 <= dim <= 1:
            raise SiteAppearanceError("dim")
        background = self._get_or_create(key)
        background.dim = dim
        background.is_enabled = is_enabled
        background.mobile_mode = mobile_mode

    def set_background_file(self, key: str, kind: str, path: str) -> str | None:
        """Use an uploaded file as the video or the poster; return the replaced address."""
        background = self._get_or_create(key)
        return self._swap_file(background, kind, path)

    def remove_background_file(self, key: str, kind: str) -> str | None:
        """Forget the video or the poster; return the removed address (to delete the file)."""
        background = self._get_or_create(key)
        return self._swap_file(background, kind, None)

    # Home texts ----------------------------------------------------------------------

    def load_home_texts(self) -> dict[str, dict[str, str]]:
        """Return what each language shows now for the editable home texts."""
        return self._language_admin.get_texts(list(HOME_TEXT_KEYS))

    def save_home_texts(self, entries: dict[str, dict[str, str]]) -> None:
        """Store the editable home texts; other keys are ignored. The caller commits."""
        allowed = {key: texts for key, texts in entries.items() if key in HOME_TEXT_KEYS}
        self._language_admin.save_texts(allowed)

    # Helpers -------------------------------------------------------------------------

    def _get_or_create(self, key: str) -> Background:
        """Return the stored background, creating an empty one for a known key."""
        if key not in BACKGROUND_KEYS:
            raise SiteAppearanceError("key")
        background = self._backgrounds.get_by_key(key)
        if background is None:
            background = self._backgrounds.add(Background(key=key, dim=DEFAULT_DIM))
            self._backgrounds.flush()
        return background

    @staticmethod
    def _swap_file(background: Background, kind: str, path: str | None) -> str | None:
        """Put `path` in the video or poster column and return the address it replaced."""
        if kind not in {"video", "poster"}:
            raise SiteAppearanceError("kind")
        column = f"{kind}_path"
        old = getattr(background, column)
        setattr(background, column, path)
        return old

    @staticmethod
    def _row(key: str, background: Background | None) -> BackgroundRow:
        """Describe a stored background, or the defaults for one that was never stored."""
        if background is None:
            return BackgroundRow(
                key, None, None, DEFAULT_DIM, True, MobileBackgroundMode.POSTER_ONLY
            )
        return BackgroundRow(
            key,
            background.video_path,
            background.poster_path,
            background.dim,
            background.is_enabled,
            background.mobile_mode,
        )
