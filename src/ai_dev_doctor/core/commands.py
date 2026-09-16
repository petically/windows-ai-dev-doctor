"""Reviewed commands only, bounded capture, no shell or inherited credentials."""

import os
import subprocess
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import BinaryIO, Protocol

from ai_dev_doctor.core.paths import is_local_path


class Command(StrEnum):
    GIT_VERSION = "git-version"


@dataclass(frozen=True)
class CommandResult:
    outcome: str
    returncode: int | None = None
    stdout: str = ""
    executable: str = ""
    truncated: bool = False


class Runner(Protocol):
    def run(self, command: Command, timeout: float) -> CommandResult: ...


def resolve_executable(name: str, env: Mapping[str, str]) -> str | None:
    # Never use Windows' implicit current-directory executable search.
    names = (name + ".exe",) if os.name == "nt" else (name,)
    for entry in env.get("PATH", "").split(os.pathsep):
        root = Path(entry.strip('"'))
        if not is_local_path(root) or root.resolve() == Path.cwd().resolve():
            continue
        for filename in names:
            candidate = root / filename
            if (
                is_local_path(candidate)
                and candidate.is_file()
                and (os.name == "nt" or os.access(candidate, os.X_OK))
            ):
                return str(candidate.resolve())
    return None


def _capture(
    argv: tuple[str, ...], env: Mapping[str, str], timeout: float, limit: int = 65536
) -> CommandResult:
    """Internal primitive; plugins cannot supply arbitrary commands through Runner."""
    if not 0.1 <= timeout <= 30 or limit < 1:
        raise ValueError("Invalid execution bounds")
    if Path(argv[0]).suffix.lower() in (".bat", ".cmd"):
        return CommandResult("blocked")
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            env=dict(env),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
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


class CommandRunner:
    def __init__(self, env: Mapping[str, str]) -> None:
        self.env = env

    def run(self, command: Command, timeout: float) -> CommandResult:
        if command is not Command.GIT_VERSION:
            raise ValueError("Unreviewed command")
        executable = resolve_executable("git", self.env)
        if executable is None:
            return CommandResult("missing")
        allowed = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "PATHEXT"}
        safe_env = {k: v for k, v in self.env.items() if k.upper() in allowed}
        safe_env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1", "LC_ALL": "C"})
        return _capture((executable, "--version"), safe_env, timeout)
