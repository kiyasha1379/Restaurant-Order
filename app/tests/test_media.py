"""Photo uploads: only real, reasonably sized pictures are kept, always re-encoded as WebP."""

from io import BytesIO

import pytest
from PIL import Image

from restaurant.media import ImageProblem, ImageStorage, InvalidImageError
from tests.helpers import make_image_bytes


@pytest.fixture
def storage(tmp_path) -> ImageStorage:
    return ImageStorage(tmp_path / "uploads")


def save(storage: ImageStorage, data: bytes) -> str:
    return storage.save(BytesIO(data))


@pytest.mark.parametrize("image_format", ["PNG", "JPEG", "WEBP"])
def test_real_pictures_are_stored_as_webp(storage, tmp_path, image_format) -> None:
    path = save(storage, make_image_bytes(image_format))
    assert path.startswith("uploads/dishes/") and path.endswith(".webp")
    stored = tmp_path / "uploads" / "dishes" / path.rsplit("/", 1)[1]
    with Image.open(stored) as picture:
        assert picture.format == "WEBP"


def test_large_pictures_are_shrunk(storage, tmp_path) -> None:
    path = save(storage, make_image_bytes("PNG", (3000, 2000)))
    with Image.open(tmp_path / "uploads" / path.removeprefix("uploads/")) as picture:
        assert max(picture.size) == 1200


def test_names_are_random_and_unique(storage) -> None:
    data = make_image_bytes()
    assert save(storage, data) != save(storage, data)


@pytest.mark.parametrize(
    ("data", "problem"),
    [
        (b"", ImageProblem.EMPTY),
        (
            b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
            ImageProblem.NOT_AN_IMAGE,
        ),
        (b"just some text pretending to be a picture", ImageProblem.NOT_AN_IMAGE),
        (make_image_bytes("PNG")[:200], ImageProblem.NOT_AN_IMAGE),
        (make_image_bytes("GIF"), ImageProblem.WRONG_TYPE),
        (make_image_bytes("BMP"), ImageProblem.WRONG_TYPE),
        (make_image_bytes("PNG", (100, 100)), ImageProblem.TOO_SMALL),
        (make_image_bytes("PNG", (6000, 8000), mode="L"), ImageProblem.TOO_MANY_PIXELS),
        (b"x" * (5 * 1024 * 1024 + 1), ImageProblem.TOO_LARGE),
    ],
    ids=["empty", "svg", "text", "truncated", "gif", "bmp", "small", "huge", "big-file"],
)
def test_bad_uploads_are_refused_with_a_reason(storage, tmp_path, data, problem) -> None:
    with pytest.raises(InvalidImageError) as error:
        save(storage, data)
    assert error.value.problem is problem
    assert not (tmp_path / "uploads").exists() or not list((tmp_path / "uploads").rglob("*.webp"))


def test_metadata_is_dropped_and_orientation_applied(storage, tmp_path) -> None:
    picture = Image.new("RGB", (400, 200), (10, 20, 30))
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 degrees when displayed
    exif[0x010F] = "SecretCameraMaker"
    buffer = BytesIO()
    picture.save(buffer, format="JPEG", exif=exif)
    path = save(storage, buffer.getvalue())
    with Image.open(tmp_path / "uploads" / path.removeprefix("uploads/")) as stored:
        assert stored.size == (200, 400)
        assert not stored.getexif()


def test_delete_removes_only_files_inside_the_upload_folder(storage, tmp_path) -> None:
    path = save(storage, make_image_bytes())
    outside = tmp_path / "secret.txt"
    outside.write_text("keep me")
    assert storage.delete(path) is True
    assert storage.delete(path) is False
    assert storage.delete("uploads/../secret.txt") is False
    assert storage.delete("../secret.txt") is False
    assert storage.delete(None) is False
    assert outside.read_text() == "keep me"
