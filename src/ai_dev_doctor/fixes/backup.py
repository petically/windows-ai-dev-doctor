"""The initial fix only backs up this tool's validated configuration."""

import hashlib
import os
import uuid
from pathlib import Path

from ai_dev_doctor.core.config import parse_config
from ai_dev_doctor.core.logging import write_event
from ai_dev_doctor.core.redaction import Redactor
from ai_dev_doctor.core.safety import SafetyError as SafetyError
from ai_dev_doctor.core.safety import validate_fix_path as _safe_path
from ai_dev_doctor.fixes.models import FixPlan


def _read(path: Path) -> tuple[bytes, tuple[int, int, int]]:
    _safe_path(path, file_required=True)
    with path.open("rb") as stream:
        info = os.fstat(stream.fileno())
        data = stream.read(65537)
    parse_config(data)
    return data, (info.st_dev, info.st_ino, info.st_mtime_ns)


class BackupConfig:
    id = "backup-config"

    def __init__(self, allowed_source: Path) -> None:
        self.allowed_source = allowed_source.absolute()

    def plan(self) -> FixPlan:
        data, identity = _read(self.allowed_source)
        suffix = uuid.uuid4().hex[:12]
        return FixPlan(
            self.allowed_source,
            self.allowed_source.with_name(f"config.toml.{suffix}.bak"),
            self.allowed_source.with_name(f"fix-{suffix}.jsonl"),
            hashlib.sha256(data).hexdigest(),
            identity,
        )

    def execute(self, plan: FixPlan, *, confirmed: bool, redactor: Redactor) -> None:
        if not confirmed:
            raise SafetyError("Explicit confirmation is required")
        if (
            plan.source != self.allowed_source
            or plan.backup.parent != self.allowed_source.parent
            or plan.audit.parent != self.allowed_source.parent
        ):
            raise SafetyError("Plan target is outside the approved scope")
        if (
            not plan.backup.name.startswith("config.toml.")
            or plan.backup.suffix != ".bak"
            or not plan.audit.name.startswith("fix-")
            or plan.audit.suffix != ".jsonl"
        ):
            raise SafetyError("Invalid backup or audit target")
        data, identity = _read(plan.source)
        if hashlib.sha256(data).hexdigest() != plan.digest or identity != plan.identity:
            raise SafetyError("Configuration changed after planning; create a new plan")
        for path in (plan.backup, plan.audit):
            _safe_path(path)
            if path.exists():
                raise SafetyError("Destination already exists; nothing overwritten")
        # Failure to establish the intent log prevents the backup operation.
        with plan.audit.open("x", encoding="utf-8") as audit:
            write_event(audit, redactor, "fix-intent", fix_id=self.id, backup=str(plan.backup))
            os.fsync(audit.fileno())
            try:
                # Recheck after audit creation and immediately before mutation.
                current, current_identity = _read(plan.source)
                if current != data or current_identity != identity:
                    raise SafetyError("Configuration changed before execution")
                _safe_path(plan.backup)
                with plan.backup.open("xb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            except (OSError, ValueError):
                write_event(audit, redactor, "fix-failed", fix_id=self.id)
                raise
            try:
                write_event(audit, redactor, "fix-completed", fix_id=self.id)
                os.fsync(audit.fileno())
            except OSError:
                raise SafetyError(
                    "Backup created but completion audit failed; inspect the shown backup"
                ) from None
