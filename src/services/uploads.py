"""Storage helpers for entity photos.

Files are written under ``static/uploads`` (served at ``/static/uploads/...``)
and the stored filename is what we persist on the model. In Docker this folder
is backed by a named volume so uploads survive container rebuilds.
"""

import uuid
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile, status

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "uploads"

# Map the accepted content types to the extension we store on disk.
ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}

# Accepted filename extensions, used as a fallback when the client does not
# send a recognised image content type (some clients send octet-stream).
ALLOWED_EXT = {
    ".jpg": ".jpg",
    ".jpeg": ".jpg",
    ".png": ".png",
    ".gif": ".gif",
    ".webp": ".webp",
}

MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def _resolve_ext(file: UploadFile) -> Optional[str]:
    ext = ALLOWED_TYPES.get(file.content_type or "")
    if ext is not None:
        return ext
    suffix = Path(file.filename or "").suffix.lower()
    return ALLOWED_EXT.get(suffix)


def save_upload(
    file: UploadFile, prefix: str, entity_id: int, old: Optional[str] = None
) -> str:
    """Validate and store an uploaded image, returning the stored filename.

    Deletes ``old`` (the previous photo) first so we never leak files.
    """
    ext = _resolve_ext(file)
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type (use JPEG, PNG, GIF or WEBP)",
        )

    data = file.file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large (max 5 MB)",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if old:
        delete_upload(old)

    # A random suffix guarantees a fresh URL so browsers never show a stale
    # cached image after a replace.
    name = f"{prefix}_{entity_id}_{uuid.uuid4().hex[:8]}{ext}"
    (UPLOAD_DIR / name).write_bytes(data)
    return name


def delete_upload(name: Optional[str]) -> None:
    """Remove a stored file if it exists; never raise on a missing file."""
    if not name:
        return
    try:
        (UPLOAD_DIR / name).unlink(missing_ok=True)
    except OSError:
        pass
