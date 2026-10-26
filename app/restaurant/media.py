"""Uploaded photos: check them, shrink them and keep them under the upload folder.

The uploaded file name, extension and declared type are never trusted. The bytes are
opened with Pillow, must really be a JPEG, PNG or WebP picture of a sensible size,
and are saved again as a smaller WebP under a random name (which also drops metadata
such as GPS positions).
"""

import secrets
from enum import StrEnum
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 40_000_000
MIN_SIDE = 200
MAX_SIDE_AFTER_RESIZE = 1200
WEBP_QUALITY = 82
ALLOWED_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})
RANDOM_NAME_BYTES = 8
STORED_EXTENSION = ".webp"


class ImageProblem(StrEnum):
    """Why a photo was refused; each value is part of a translation key."""

    EMPTY = "empty"
    TOO_LARGE = "too_large"
    NOT_AN_IMAGE = "not_an_image"
    WRONG_TYPE = "wrong_type"
    TOO_SMALL = "too_small"
    TOO_MANY_PIXELS = "too_many_pixels"


class InvalidImageError(ValueError):
    """The uploaded photo was refused; `problem` says why."""

    def __init__(self, problem: ImageProblem) -> None:
        """Keep the reason so the form can show a message in the page language."""
        super().__init__(problem.value)
        self.problem = problem


class ImageStorage:
    """Saves checked photos below `root` and returns their address relative to `static/`."""

    def __init__(self, root: Path, folder: str = "dishes", url_prefix: str = "uploads") -> None:
        """Receive the upload root, so tests can use a temporary folder."""
        self._root = Path(root)
        self._folder = folder
        self._url_prefix = url_prefix

    def save(self, stream: BinaryIO) -> str:
        """Check and store one photo; return its address such as 'uploads/dishes/ab.webp'.

        Raises InvalidImageError when the photo is not acceptable.
        """
        picture = self._open(stream)
        name = f"{secrets.token_hex(RANDOM_NAME_BYTES)}{STORED_EXTENSION}"
        target = self._root / self._folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        picture.save(target, format="WEBP", quality=WEBP_QUALITY, method=4)
        return f"{self._url_prefix}/{self._folder}/{name}"

    def delete(self, relative_path: str | None) -> bool:
        """Remove a stored photo and return True; paths outside the upload folder are ignored."""
        if not relative_path or not relative_path.startswith(f"{self._url_prefix}/"):
            return False
        target = (self._root / relative_path.removeprefix(f"{self._url_prefix}/")).resolve()
        if not target.is_relative_to(self._root.resolve()) or not target.is_file():
            return False
        target.unlink()
        return True

    @staticmethod
    def _open(stream: BinaryIO) -> Image.Image:
        """Read, verify and shrink the upload; raise InvalidImageError if it is not acceptable."""
        data = stream.read(MAX_UPLOAD_BYTES + 1)
        if not data:
            raise InvalidImageError(ImageProblem.EMPTY)
        if len(data) > MAX_UPLOAD_BYTES:
            raise InvalidImageError(ImageProblem.TOO_LARGE)
        try:
            with Image.open(BytesIO(data)) as probe:
                image_format, (width, height) = probe.format, probe.size
                probe.verify()
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
            raise InvalidImageError(ImageProblem.NOT_AN_IMAGE) from error
        if image_format not in ALLOWED_FORMATS:
            raise InvalidImageError(ImageProblem.WRONG_TYPE)
        if width * height > MAX_PIXELS:
            raise InvalidImageError(ImageProblem.TOO_MANY_PIXELS)
        if min(width, height) < MIN_SIDE:
            raise InvalidImageError(ImageProblem.TOO_SMALL)
        try:
            picture = Image.open(BytesIO(data))
            picture.load()
        except (OSError, SyntaxError, ValueError) as error:
            raise InvalidImageError(ImageProblem.NOT_AN_IMAGE) from error
        picture = ImageOps.exif_transpose(picture)
        picture.thumbnail((MAX_SIDE_AFTER_RESIZE, MAX_SIDE_AFTER_RESIZE), Image.Resampling.LANCZOS)
        return picture.convert("RGBA" if "A" in picture.getbands() else "RGB")
