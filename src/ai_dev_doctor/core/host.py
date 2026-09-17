"""Minimal read-only host boundary; add platform APIs when a check needs them."""

import os
import platform
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from ai_dev_doctor.core.paths import is_local_path


class Host(Protocol):
    @property
    def environment(self) -> Mapping[str, str]: ...
    def system(self) -> tuple[str, str, str]: ...
    def directory_exists(self, path: str) -> bool | None: ...


class LocalHost:
    @property
    def environment(self) -> Mapping[str, str]:
        return dict(os.environ)

    def system(self) -> tuple[str, str, str]:
        return platform.system(), platform.version(), platform.machine()

    def directory_exists(self, path: str) -> bool | None:
        candidate = Path(path)
        try:
            return candidate.is_dir() if is_local_path(candidate) else None
        except OSError:
            return None
