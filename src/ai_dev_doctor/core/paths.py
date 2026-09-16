"""Avoid implicitly contacting remote shares while inspecting local PATH."""

import sys
from pathlib import Path


def is_local_path(path: Path) -> bool:
    if not path.is_absolute():
        return False
    if sys.platform != "win32":
        return True
    import ctypes

    # Do not traverse UNC, mapped network drives or filesystem reparse points.
    if str(path).startswith(("\\\\", "//")):
        return False
    if ctypes.windll.kernel32.GetDriveTypeW(str(path.anchor)) not in (2, 3, 5, 6):
        return False
    for item in (*reversed(path.parents), path):
        try:
            info = item.lstat()
        except FileNotFoundError:
            return True
        except OSError:
            return False
        if getattr(info, "st_file_attributes", 0) & 0x400:
            return False
    return True
