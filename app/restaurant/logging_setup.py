"""Logging setup: console always, a rotating file when the config asks for it."""

import logging
from logging.handlers import RotatingFileHandler

from flask import Flask

from restaurant.config import INSTANCE_DIR

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
LOG_FILE_MAX_BYTES = 1_000_000
LOG_FILE_BACKUP_COUNT = 3


def configure_logging(app: Flask) -> None:
    """Attach handlers to the app logger according to the active configuration."""
    # Several apps can be created in one process (tests); avoid duplicate handlers.
    app.logger.handlers.clear()
    app.logger.setLevel(app.config["LOG_LEVEL"])
    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    app.logger.addHandler(console_handler)

    if app.config["LOG_TO_FILE"]:
        log_directory = INSTANCE_DIR / "logs"
        log_directory.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_directory / "app.log",
            maxBytes=LOG_FILE_MAX_BYTES,
            backupCount=LOG_FILE_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)
