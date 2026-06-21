"""Route uploaded files to the correct Kimi Files purpose."""

from __future__ import annotations

from pathlib import Path


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".svg"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def route_kimi_file_purpose(
    *,
    filename: str,
    mime_type: str | None = None,
    execution_profile: str | None = None,
) -> str:
    suffix = Path(filename).suffix.lower()
    if execution_profile == "batch_eval" or suffix == ".jsonl":
        return "batch"
    if mime_type and mime_type.startswith("image/"):
        return "image"
    if mime_type and mime_type.startswith("video/"):
        return "video"
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    return "file-extract"
