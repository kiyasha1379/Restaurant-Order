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


def delete_upload(root: Path, url_prefix: str, relative_path: str | None) -> bool:
    """Remove a stored upload and return True; paths outside the upload folder are ignored."""
    if not relative_path or not relative_path.startswith(f"{url_prefix}/"):
        return False
    target = (root / relative_path.removeprefix(f"{url_prefix}/")).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        return False
    target.unlink()
    return True


class ImageStorage:
    """Saves checked photos below `root` and returns their address relative to `static/`."""

    def __init__(
        self,
        root: Path,
        folder: str = "dishes",
        url_prefix: str = "uploads",
        max_side: int = MAX_SIDE_AFTER_RESIZE,
    ) -> None:
        """Receive the upload root, so tests can use a temporary folder."""
        self._root = Path(root)
        self._folder = folder
        self._url_prefix = url_prefix
        self._max_side = max_side

    def save(self, stream: BinaryIO) -> str:
        """Check and store one photo; return its address such as 'uploads/dishes/ab.webp'.

        Raises InvalidImageError when the photo is not acceptable.
        """
        picture = self._open(stream, self._max_side)
        name = f"{secrets.token_hex(RANDOM_NAME_BYTES)}{STORED_EXTENSION}"
        target = self._root / self._folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        picture.save(target, format="WEBP", quality=WEBP_QUALITY, method=4)
        return f"{self._url_prefix}/{self._folder}/{name}"

    def delete(self, relative_path: str | None) -> bool:
        """Remove a stored photo and return True; paths outside the upload folder are ignored."""
        return delete_upload(self._root, self._url_prefix, relative_path)

    @staticmethod
    def _open(stream: BinaryIO, max_side: int) -> Image.Image:
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
        picture.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        return picture.convert("RGBA" if "A" in picture.getbands() else "RGB")


class VideoProblem(StrEnum):
    """Why a background video was refused; each value is part of a translation key."""

    EMPTY = "empty"
    TOO_LARGE = "too_large"
    NOT_A_VIDEO = "not_a_video"


class InvalidVideoError(ValueError):
    """The uploaded video was refused; `problem` says why."""

    def __init__(self, problem: VideoProblem) -> None:
        """Keep the reason so the form can show a message in the page language."""
        super().__init__(problem.value)
        self.problem = problem


MAX_VIDEO_BYTES = 12 * 1024 * 1024
MP4_SIGNATURE_OFFSET = 4
MP4_SIGNATURE = b"ftyp"
VIDEO_EXTENSION = ".mp4"


class VideoStorage:
    """Saves checked MP4 videos below `root` under a random name.

    The file name and declared type are not trusted: the bytes must start with an MP4
    "ftyp" box and stay under the size limit. The video is stored as it is (re-encoding
    is not done here), so staff should upload a short, already compressed clip.
    """

    def __init__(
        self, root: Path, folder: str = "backgrounds", url_prefix: str = "uploads"
    ) -> None:
        """Receive the upload root, so tests can use a temporary folder."""
        self._root = Path(root)
        self._folder = folder
        self._url_prefix = url_prefix

    def save(self, stream: BinaryIO) -> str:
        """Check and store one video; return its address such as 'uploads/backgrounds/ab.mp4'.

        Raises InvalidVideoError when the file is not acceptable.
        """
        data = stream.read(MAX_VIDEO_BYTES + 1)
        if not data:
            raise InvalidVideoError(VideoProblem.EMPTY)
        if len(data) > MAX_VIDEO_BYTES:
            raise InvalidVideoError(VideoProblem.TOO_LARGE)
        signature = data[MP4_SIGNATURE_OFFSET : MP4_SIGNATURE_OFFSET + len(MP4_SIGNATURE)]
        if signature != MP4_SIGNATURE:
            raise InvalidVideoError(VideoProblem.NOT_A_VIDEO)
        name = f"{secrets.token_hex(RANDOM_NAME_BYTES)}{VIDEO_EXTENSION}"
        target = self._root / self._folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return f"{self._url_prefix}/{self._folder}/{name}"

    def delete(self, relative_path: str | None) -> bool:
        """Remove a stored video and return True; paths outside the upload folder are ignored."""
        return delete_upload(self._root, self._url_prefix, relative_path)
