"""Wipe the demo database so `flask reset-demo` can start again from the sample data.

This is the one place that deletes whole tables, so it only works on a demo installation
(the command checks DEMO_MODE before it builds this object).
"""

from pathlib import Path

from sqlalchemy.orm import Session

from restaurant.constants import LANGUAGE_CODE_PERSIAN
from restaurant.models import Language

# Tables that keep their rows: the two language rows come from the first migration.
KEPT_TABLES = frozenset({"languages", "alembic_version"})
KEPT_UPLOAD_FILES = frozenset({".gitkeep"})


class DemoWiper:
    """Empties every table (except the two languages) and removes uploaded files."""

    def __init__(self, session: Session, tables: list, upload_folder: Path) -> None:
        """Receive the session, the tables in dependency order and the upload folder."""
        self._session = session
        self._tables = tables
        self._upload_folder = Path(upload_folder)

    def wipe(self) -> int:
        """Delete all rows and uploaded files; return how many files were removed.

        Both languages go back to their starting state (Persian default, both on).
        The caller commits.
        """
        for table in reversed(self._tables):
            if table.name not in KEPT_TABLES:
                self._session.execute(table.delete())
        for language in self._session.query(Language):
            language.is_enabled = True
            language.is_default = language.code == LANGUAGE_CODE_PERSIAN
        return self._remove_uploads()

    def _remove_uploads(self) -> int:
        """Delete every uploaded file below the upload folder (not the folders)."""
        removed = 0
        if not self._upload_folder.is_dir():
            return removed
        for path in self._upload_folder.rglob("*"):
            if path.is_file() and path.name not in KEPT_UPLOAD_FILES:
                path.unlink()
                removed += 1
        return removed
