"""Safe filesystem paths for admin PDF uploads."""

from __future__ import annotations

import os
import uuid


class UnsafeUploadFilename(ValueError):
    """Raised when an upload filename would escape the upload directory."""


def sanitize_pdf_filename(original: str | None) -> str:
    """
    Return a basename-only PDF filename.

    Rejects missing names, non-PDFs, and path components that could
    traverse out of the upload directory when joined with a UUID prefix.
    """
    if original is None or not str(original).strip():
        raise UnsafeUploadFilename("Missing filename")

    # Normalize Windows separators before basename so "a\\b.pdf" collapses.
    name = os.path.basename(str(original).replace("\\", "/").strip())
    if not name or name in (".", ".."):
        raise UnsafeUploadFilename("Invalid filename")
    if not name.lower().endswith(".pdf"):
        raise UnsafeUploadFilename("Only PDF files are accepted")
    if "/" in name or "\\" in name:
        raise UnsafeUploadFilename("Invalid filename")
    return name


def build_upload_path(upload_dir: str, original_filename: str | None) -> tuple[str, str]:
    """
    Build a unique path under upload_dir for an uploaded PDF.

    Returns (safe_display_filename, absolute_file_path).
    Guarantees the resolved path stays inside upload_dir.
    """
    safe_name = sanitize_pdf_filename(original_filename)
    os.makedirs(upload_dir, exist_ok=True)
    abs_upload = os.path.abspath(upload_dir)
    unique = f"{uuid.uuid4()}_{safe_name}"
    file_path = os.path.abspath(os.path.join(abs_upload, unique))
    if os.path.commonpath([abs_upload, file_path]) != abs_upload:
        raise UnsafeUploadFilename("Invalid filename")
    return safe_name, file_path
