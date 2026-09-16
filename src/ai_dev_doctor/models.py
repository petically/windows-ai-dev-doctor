"""Public immutable diagnostic contracts (report schema version 1)."""

import re
from dataclasses import dataclass
from enum import StrEnum


class Status(StrEnum):
    PASS = "PASS"
    INFO = "INFO"
    WARNING = "WARNING"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class CheckResult:
    id: str
    name: str
    category: str
    status: Status
    summary: str
    details: tuple[str, ...] = ()
    severity: Severity = Severity.INFO
    evidence: tuple[tuple[str, str], ...] = ()
    recommendations: tuple[str, ...] = ()
    fix_ids: tuple[str, ...] = ()
    documentation_url: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", self.id):
            raise ValueError("Invalid check ID")
        if any(
            not isinstance(value, str) or not value.strip()
            for value in (self.name, self.category, self.summary)
        ):
            raise ValueError("Result text fields must be nonempty strings")
        if self.documentation_url is not None and not isinstance(self.documentation_url, str):
            raise ValueError("Documentation URL must be a string or None")
        if not isinstance(self.status, Status) or not isinstance(self.severity, Severity):
            raise ValueError("Status and severity must be enum values")
        for items in (self.details, self.recommendations, self.fix_ids):
            if not isinstance(items, tuple) or any(not isinstance(v, str) for v in items):
                raise ValueError("Result collections must be immutable strings")
        if not isinstance(self.evidence, tuple) or any(
            not isinstance(pair, tuple)
            or len(pair) != 2
            or any(not isinstance(v, str) for v in pair)
            for pair in self.evidence
        ):
            raise ValueError("Evidence must be immutable string pairs")


def exit_code(results: tuple[CheckResult, ...]) -> int:
    return int(any(r.status in (Status.FAIL, Status.ERROR) for r in results))
