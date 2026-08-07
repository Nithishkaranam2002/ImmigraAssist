"""Regression tests for admin PDF upload path sanitization."""

import os
from pathlib import Path

import pytest

from app.services.upload_paths import (
    UnsafeUploadFilename,
    build_upload_path,
    sanitize_pdf_filename,
)


def test_sanitize_accepts_plain_pdf_name():
    assert sanitize_pdf_filename("Policy Manual.pdf") == "Policy Manual.pdf"


def test_sanitize_strips_directory_components():
    assert sanitize_pdf_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_pdf_filename("foo/../../../tmp/evil.pdf") == "evil.pdf"
    assert sanitize_pdf_filename("subdir\\nested\\doc.pdf") == "doc.pdf"


def test_sanitize_rejects_non_pdf_and_missing():
    with pytest.raises(UnsafeUploadFilename, match="Only PDF"):
        sanitize_pdf_filename("notes.txt")
    with pytest.raises(UnsafeUploadFilename, match="Missing"):
        sanitize_pdf_filename(None)
    with pytest.raises(UnsafeUploadFilename, match="Missing"):
        sanitize_pdf_filename("   ")


def test_build_upload_path_stays_inside_upload_dir(tmp_path: Path):
    upload_dir = tmp_path / "uploads"
    safe_name, file_path = build_upload_path(
        str(upload_dir), "../../../tmp/pwned.pdf"
    )
    assert safe_name == "pwned.pdf"
    abs_upload = os.path.abspath(str(upload_dir))
    abs_file = os.path.abspath(file_path)
    assert os.path.commonpath([abs_upload, abs_file]) == abs_upload
    assert abs_file.startswith(abs_upload + os.sep)
    assert os.path.basename(abs_file).endswith("_pwned.pdf")


def test_build_upload_path_rejects_escape_after_uuid_prefix(tmp_path: Path, monkeypatch):
    """Defense in depth if sanitize were bypassed with a crafted name."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    def _unsafe(_original):
        return "../../../outside.pdf"

    monkeypatch.setattr(
        "app.services.upload_paths.sanitize_pdf_filename", _unsafe
    )
    with pytest.raises(UnsafeUploadFilename, match="Invalid"):
        build_upload_path(str(upload_dir), "ignored.pdf")
