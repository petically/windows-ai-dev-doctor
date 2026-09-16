"""Fix registration separates planning from confirmed execution.

Plans are data owned by each operation; there is no generic shell/delete repair primitive.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ai_dev_doctor.core.redaction import Redactor
from ai_dev_doctor.fixes.backup import BackupConfig
from ai_dev_doctor.fixes.models import FixPlan


class Fix(Protocol):
    def plan(self) -> FixPlan: ...
    def execute(self, plan: FixPlan, *, confirmed: bool, redactor: Redactor) -> None: ...


@dataclass(frozen=True)
class FixDefinition:
    id: str
    create: Callable[[Path], Fix]


DEFINITIONS = (FixDefinition("backup-config", BackupConfig),)


def get_fix(fix_id: str, config: Path) -> Fix:
    for definition in DEFINITIONS:
        if definition.id == fix_id:
            return definition.create(config)
    raise ValueError("Unknown fix ID")
