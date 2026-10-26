"""Backgrounds: finds the video/poster for a page section by key."""

from dataclasses import dataclass

from restaurant.constants import MobileBackgroundMode
from restaurant.repositories import BackgroundRepository


@dataclass(frozen=True)
class BackgroundView:
    """What the background macro needs. Paths are relative to the static folder."""

    key: str
    video_path: str | None
    poster_path: str | None
    dim: float
    mobile_mode: MobileBackgroundMode


class BackgroundService:
    """Reads backgrounds; a missing or switched-off one simply has no view."""

    def __init__(self, background_repository: BackgroundRepository) -> None:
        """Receive the repository instead of importing it, so tests can swap it."""
        self._background_repository = background_repository

    def find(self, key: str) -> BackgroundView | None:
        """Return the enabled background with this key, or None (the page then draws a gradient)."""
        background = self._background_repository.get_by_key(key)
        if background is None or not background.is_enabled:
            return None
        return BackgroundView(
            key=background.key,
            video_path=background.video_path,
            poster_path=background.poster_path,
            dim=background.dim,
            mobile_mode=background.mobile_mode,
        )
