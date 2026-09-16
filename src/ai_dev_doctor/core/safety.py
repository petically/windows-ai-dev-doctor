"""Centralized filesystem guards for explicitly authorized repairs."""

import stat
from pathlib import Path


class SafetyError(ValueError):
    pass


def validate_fix_path(path: Path, *, file_required: bool = False) -> None:
    if not path.is_absolute():
        raise SafetyError("Fix paths must be absolute")
    for item in (*reversed(path.parents), path):
        try:
            info = item.lstat()
        except FileNotFoundError:
            if item == path and not file_required:
                continue
            raise SafetyError("Required parent or source is missing") from None
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise SafetyError("Symlinks and Windows reparse points are not eligible for fixes")
        if item == path and file_required and not stat.S_ISREG(info.st_mode):
            raise SafetyError("Source must be a regular file")
