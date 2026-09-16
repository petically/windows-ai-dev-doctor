from collections.abc import Mapping
from dataclasses import dataclass, field

import pytest

from ai_dev_doctor.core.commands import Command, CommandResult, Executable, Tool
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
        if command is Command.GIT_VERSION:
            return self.result
        fixtures = {
            Command.GIT_IDENTITY_KEYS: CommandResult(
                "completed", 0, "user.name\nuser.email\n", "git.exe"
            ),
            Command.GIT_DEFAULT_BRANCH: CommandResult("completed", 0, "main\n", "git.exe"),
            Command.GIT_CREDENTIAL_HELPER_KEYS: CommandResult(
                "completed", 0, "credential.helper\n", "git.exe"
            ),
            Command.GIT_REPOSITORY: CommandResult("completed", 128, "", "git.exe"),
            Command.POWERSHELL_VERSION: CommandResult(
                "completed", 0, "5.1.22621.2506", "powershell.exe"
            ),
        }
        return fixtures.get(command, CommandResult("missing"))

    def locations(self, tool: Tool) -> tuple[Executable, ...]:
        if tool is Tool.GIT and self.result.outcome != "missing":
            return (Executable(r"C:\Tools\git.exe", True),)
        if tool is Tool.POWERSHELL:
            return (Executable(r"C:\Windows\powershell.exe", True),)
        return ()


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
