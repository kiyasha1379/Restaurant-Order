"""The `site_sections` table: order and visibility of the movable home page sections."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from restaurant.extensions import db


class SiteSection(db.Model):
    """One movable home section. A missing row means "visible, in the default place"."""

    __tablename__ = "site_sections"

    key: Mapped[str] = mapped_column(String(30), primary_key=True)
    position: Mapped[int] = mapped_column(default=0)
    is_visible: Mapped[bool] = mapped_column(default=True)
