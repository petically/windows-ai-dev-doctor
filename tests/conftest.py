from collections.abc import Mapping
from dataclasses import dataclass, field

import pytest

from ai_dev_doctor.core.commands import Command, CommandResult
from ai_dev_doctor.core.config import Config
from ai_dev_doctor.core.engine import Context
from ai_dev_doctor.core.network import ProbeKind, ProbeResult


@dataclass
class FakeHost:
    environment: Mapping[str, str] = field(default_factory=lambda: {"PATH": r"C:\Tools"})
    platform: str = "Windows"

    def system(self) -> tuple[str, str, str]:
        return self.platform, "10.0.22631", "AMD64"

    def directory_exists(self, path: str) -> bool:
        return path.lower() == r"c:\tools"


@dataclass
class FakeRunner:
    result: CommandResult = CommandResult(
        "completed", 0, "git version 2.49.0.windows.1\n", "git.exe"
    )

    def run(self, command: Command, timeout: float) -> CommandResult:
        assert command == Command.GIT_VERSION
        return self.result


@dataclass
class FakeNetwork:
    calls: list[str] = field(default_factory=list)
    ok: bool = True

    def probe(self, kind: ProbeKind, target: str, timeout: float) -> ProbeResult:
        self.calls.append(target)
        return ProbeResult(target, kind, self.ok, "fixture", 1)


@pytest.fixture
def context() -> Context:
    return Context(FakeHost(), FakeRunner(), FakeNetwork(), Config())
