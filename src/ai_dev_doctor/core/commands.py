"""Reviewed commands only, bounded capture, no shell or inherited credentials."""

import os
import subprocess
import sys
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import BinaryIO, Protocol

from ai_dev_doctor.core.paths import is_local_path


class Tool(StrEnum):
    GIT = "git"
    GH = "gh"
    PYTHON = "python"
    PY_LAUNCHER = "py"
    PIP = "pip"
    NODE = "node"
    NPM = "npm"
    NPX = "npx"
    POWERSHELL = "powershell"
    PWSH = "pwsh"
    CODEX = "codex"
    TERMINAL = "wt"
    NVM = "nvm"
    FNM = "fnm"


class Command(StrEnum):
    GIT_VERSION = "git-version"
    GIT_IDENTITY_KEYS = "git-identity-keys"
    GIT_DEFAULT_BRANCH = "git-default-branch"
    GIT_CREDENTIAL_HELPER_KEYS = "git-credential-helper-keys"
    GIT_REPOSITORY = "git-repository"
    GH_VERSION = "gh-version"
    GH_AUTH_STATUS = "gh-auth-status"
    PYTHON_VERSION = "python-version"
    PY_LAUNCHER_VERSION = "py-launcher-version"
    PIP_VERSION = "pip-version"
    NODE_VERSION = "node-version"
    NPM_VERSION = "npm-version"
    NPX_VERSION = "npx-version"
    POWERSHELL_VERSION = "powershell-version"
    PWSH_VERSION = "pwsh-version"
    CODEX_VERSION = "codex-version"


@dataclass(frozen=True)
class CommandResult:
    outcome: str
    returncode: int | None = None
    stdout: str = ""
    executable: str = ""
    truncated: bool = False


@dataclass(frozen=True)
class Executable:
    path: str
    runnable: bool


class Runner(Protocol):
    def run(self, command: Command, timeout: float) -> CommandResult: ...
    def locations(self, tool: Tool) -> tuple[Executable, ...]: ...


def resolve_executables(name: str, env: Mapping[str, str]) -> tuple[Executable, ...]:
    """Resolve every local PATH match without current-directory or shell lookup."""
    names = (
        (name + ".exe", name + ".com", name + ".cmd", name + ".bat") if os.name == "nt" else (name,)
    )
    found: list[Executable] = []
    seen: set[str] = set()
    for entry in env.get("PATH", "").split(os.pathsep):
        root = Path(entry.strip('"'))
        try:
            if not is_local_path(root) or root.resolve() == Path.cwd().resolve():
                continue
        except OSError:
            continue
        for filename in names:
            candidate = root / filename
            try:
                runnable = candidate.suffix.casefold() not in (".bat", ".cmd")
                if (
                    is_local_path(candidate)
                    and candidate.is_file()
                    and (os.name == "nt" or os.access(candidate, os.X_OK))
                ):
                    resolved = str(candidate.resolve())
                    key = os.path.normcase(resolved)
                    if key not in seen:
                        found.append(Executable(resolved, runnable))
                        seen.add(key)
            except OSError:
                continue
    return tuple(found)


def resolve_executable(name: str, env: Mapping[str, str]) -> str | None:
    return next((item.path for item in resolve_executables(name, env) if item.runnable), None)


def _capture(
    argv: tuple[str, ...], env: Mapping[str, str], timeout: float, limit: int = 65536
) -> CommandResult:
    """Internal primitive; plugins cannot supply arbitrary commands through Runner."""
    if not 0.1 <= timeout <= 30 or limit < 1:
        raise ValueError("Invalid execution bounds")
    if Path(argv[0]).suffix.lower() in (".bat", ".cmd"):
        return CommandResult("blocked")
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            env=dict(env),
            creationflags=creationflags,
        )
    except FileNotFoundError:
        return CommandResult("missing")
    except OSError:
        return CommandResult("unavailable")
    output = bytearray()
    overflow = threading.Event()

    def drain(stream: BinaryIO, keep: bool) -> None:
        try:
            while chunk := stream.read(4096):
                if keep:
                    available = max(0, limit - len(output))
                    output.extend(chunk[:available])
                    if len(chunk) > available:
                        overflow.set()
        except (OSError, ValueError):
            pass
        finally:
            stream.close()

    assert proc.stdout is not None and proc.stderr is not None
    readers = [
        threading.Thread(target=drain, args=(proc.stdout, True), daemon=True),
        threading.Thread(target=drain, args=(proc.stderr, False), daemon=True),
    ]
    for reader in readers:
        reader.start()
    outcome = "completed"
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2)
        outcome = "timeout"
    for reader in readers:
        reader.join(timeout=0.2)
    if any(reader.is_alive() for reader in readers):
        outcome = "incomplete"
    return CommandResult(
        outcome,
        proc.returncode,
        bytes(output).decode("utf-8", errors="replace"),
        argv[0],
        overflow.is_set(),
    )


@dataclass(frozen=True)
class _CommandSpec:
    tool: Tool
    arguments: tuple[str, ...]


_VERSION_SCRIPT = "[Console]::Out.Write($PSVersionTable.PSVersion.ToString())"
_SPECS = {
    Command.GIT_VERSION: _CommandSpec(Tool.GIT, ("--version",)),
    Command.GIT_IDENTITY_KEYS: _CommandSpec(
        Tool.GIT, ("config", "--global", "--name-only", "--get-regexp", r"^user\.(name|email)$")
    ),
    Command.GIT_DEFAULT_BRANCH: _CommandSpec(
        Tool.GIT, ("config", "--global", "--get", "init.defaultBranch")
    ),
    Command.GIT_CREDENTIAL_HELPER_KEYS: _CommandSpec(
        Tool.GIT,
        ("config", "--global", "--name-only", "--get-regexp", r"^credential\..*helper$"),
    ),
    Command.GIT_REPOSITORY: _CommandSpec(Tool.GIT, ("status", "--porcelain=v2", "--branch")),
    Command.GH_VERSION: _CommandSpec(Tool.GH, ("--version",)),
    Command.GH_AUTH_STATUS: _CommandSpec(
        Tool.GH, ("auth", "status", "--active", "--hostname", "github.com")
    ),
    Command.PYTHON_VERSION: _CommandSpec(Tool.PYTHON, ("-I", "-S", "--version")),
    Command.PY_LAUNCHER_VERSION: _CommandSpec(Tool.PY_LAUNCHER, ("--version",)),
    Command.PIP_VERSION: _CommandSpec(Tool.PIP, ("--version",)),
    Command.NODE_VERSION: _CommandSpec(Tool.NODE, ("--version",)),
    Command.POWERSHELL_VERSION: _CommandSpec(
        Tool.POWERSHELL, ("-NoLogo", "-NoProfile", "-NonInteractive", "-Command", _VERSION_SCRIPT)
    ),
    Command.PWSH_VERSION: _CommandSpec(
        Tool.PWSH, ("-NoLogo", "-NoProfile", "-NonInteractive", "-Command", _VERSION_SCRIPT)
    ),
    Command.CODEX_VERSION: _CommandSpec(Tool.CODEX, ("--version",)),
}


class CommandRunner:
    def __init__(self, env: Mapping[str, str]) -> None:
        self.env = dict(env)

    def locations(self, tool: Tool) -> tuple[Executable, ...]:
        return resolve_executables(tool.value, self.env)

    def _environment(self) -> dict[str, str]:
        allowed = {
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "PATH",
            "PATHEXT",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "PROGRAMDATA",
        }
        safe = {key: value for key, value in self.env.items() if key.upper() in allowed}
        safe.update(
            {
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GH_PROMPT_DISABLED": "1",
                "GH_NO_UPDATE_NOTIFIER": "1",
                "GH_TELEMETRY": "0",
                "DO_NOT_TRACK": "1",
                "NO_COLOR": "1",
                "LC_ALL": "C",
            }
        )
        return safe

    def _node_package_version(self, command: Command, timeout: float) -> CommandResult:
        node = resolve_executable(Tool.NODE.value, self.env)
        if node is None:
            return CommandResult("missing")
        script_name = "npm-cli.js" if command is Command.NPM_VERSION else "npx-cli.js"
        script = Path(node).parent / "node_modules" / "npm" / "bin" / script_name
        try:
            if not is_local_path(script) or not script.is_file():
                locations = self.locations(Tool.NPM if command is Command.NPM_VERSION else Tool.NPX)
                return CommandResult("blocked" if locations else "missing")
        except OSError:
            return CommandResult("unavailable")
        return _capture((node, str(script), "--version"), self._environment(), timeout)

    def run(self, command: Command, timeout: float) -> CommandResult:
        if command in (Command.NPM_VERSION, Command.NPX_VERSION):
            return self._node_package_version(command, timeout)
        try:
            spec = _SPECS[command]
        except KeyError:
            raise ValueError("Unreviewed command") from None
        executable = resolve_executable(spec.tool.value, self.env)
        if executable is None:
            locations = self.locations(spec.tool)
            return CommandResult("blocked" if locations else "missing")
        return _capture((executable, *spec.arguments), self._environment(), timeout)
