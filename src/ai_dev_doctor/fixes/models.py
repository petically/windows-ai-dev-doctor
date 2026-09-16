"""Immutable fix plan data shared by the CLI and repair implementations."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FixPlan:
    source: Path
    backup: Path
    audit: Path
    digest: str
    identity: tuple[int, int, int]
    action: str = "Create an exclusive backup of this tool's configuration"
    reason: str = "Preserve a known configuration before manual changes"
    risk: str = "Low: creates a backup and an audit file; does not change the original"
    reversible: str = "Yes: original remains intact; restore backup manually if needed"
