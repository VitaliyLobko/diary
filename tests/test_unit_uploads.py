"""Unit tests for the photo storage helpers (src/services/uploads.py).

``UPLOAD_DIR`` is redirected to a tmp directory so nothing touches the real
static/uploads folder.
"""

from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.services import uploads


@pytest.fixture(autouse=True)
def _tmp_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(uploads, "UPLOAD_DIR", tmp_path)
    return tmp_path


def _file(content=b"binarydata", content_type="image/jpeg", filename="pic.jpg"):
    return SimpleNamespace(
        content_type=content_type, filename=filename, file=BytesIO(content)
    )


@pytest.mark.parametrize(
    "content_type,expected_ext",
    [
        ("image/jpeg", ".jpg"),
        ("image/png", ".png"),
        ("image/gif", ".gif"),
        ("image/webp", ".webp"),
    ],
)
def test_save_upload_by_content_type(_tmp_upload_dir, content_type, expected_ext):
    name = uploads.save_upload(_file(content_type=content_type), "student", 7)
    assert name.startswith("student_7_")
    assert name.endswith(expected_ext)
    assert (_tmp_upload_dir / name).read_bytes() == b"binarydata"


def test_save_upload_falls_back_to_filename_extension(_tmp_upload_dir):
    # Some clients send octet-stream; the extension should still be honoured.
    file = _file(content_type="application/octet-stream", filename="PHOTO.PNG")
    name = uploads.save_upload(file, "teacher", 3)
    assert name.endswith(".png")
    assert (_tmp_upload_dir / name).exists()


def test_save_upload_rejects_unsupported_type():
    file = _file(content_type="text/plain", filename="notes.txt")
    with pytest.raises(HTTPException) as exc:
        uploads.save_upload(file, "student", 1)
    assert exc.value.status_code == 400


def test_save_upload_rejects_oversized_file(monkeypatch):
    monkeypatch.setattr(uploads, "MAX_BYTES", 10)
    file = _file(content=b"x" * 11)
    with pytest.raises(HTTPException) as exc:
        uploads.save_upload(file, "student", 1)
    assert exc.value.status_code == 413


def test_save_upload_replaces_old_file(_tmp_upload_dir):
    first = uploads.save_upload(_file(), "student", 5)
    assert (_tmp_upload_dir / first).exists()

    second = uploads.save_upload(_file(), "student", 5, old=first)
    assert second != first
    assert (_tmp_upload_dir / second).exists()
    # the previous file must be gone, so we never leak orphaned uploads
    assert not (_tmp_upload_dir / first).exists()


def test_delete_upload_removes_file(_tmp_upload_dir):
    name = uploads.save_upload(_file(), "student", 9)
    uploads.delete_upload(name)
    assert not (_tmp_upload_dir / name).exists()


def test_delete_upload_is_a_noop_for_missing_or_none(_tmp_upload_dir):
    # Neither a missing filename nor None should raise.
    uploads.delete_upload("does-not-exist.jpg")
    uploads.delete_upload(None)
