"""The `settings` table: site-wide key/value pairs edited from the admin panel."""

from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from restaurant.extensions import db
from restaurant.timeutils import now_tehran


class Setting(db.Model):
    """A single named setting. Values are text; the services give them meaning."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(default=now_tehran, onupdate=now_tehran)
