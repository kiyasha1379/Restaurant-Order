"""The `backgrounds` table: every video/poster background on the site."""

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from restaurant.constants import MobileBackgroundMode
from restaurant.extensions import db
from restaurant.models.columns import enum_type


class Background(db.Model):
    """One background, found by `key` (for example 'home-hero' or 'menu-page').

    The fallback chain when drawing it is: video, then poster, then a dark
    gradient, so a missing file never leaves a blank page (plan, section 8).
    """

    __tablename__ = "backgrounds"
    __table_args__ = (CheckConstraint("dim >= 0 AND dim <= 1", name="dim_between_0_and_1"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(60), unique=True)
    video_path: Mapped[str | None] = mapped_column(String(255))
    poster_path: Mapped[str | None] = mapped_column(String(255))
    # Strength of the dark layer over the video: 0 = none, 1 = fully black.
    dim: Mapped[float] = mapped_column(default=0.45)
    is_enabled: Mapped[bool] = mapped_column(default=True)
    mobile_mode: Mapped[MobileBackgroundMode] = mapped_column(
        enum_type(MobileBackgroundMode), default=MobileBackgroundMode.POSTER_ONLY
    )
