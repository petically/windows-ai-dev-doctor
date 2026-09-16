import os
import sys
import time
from pathlib import Path

import pytest

from ai_dev_doctor.core.commands import Command, CommandRunner, _capture, resolve_executable


def test_command_timeout() -> None:
    start = time.monotonic()
    result = _capture((sys.executable, "-I", "-c", "import time; time.sleep(10)"), os.environ, 0.1)
    assert result.outcome == "timeout"
    assert time.monotonic() - start < 4


def test_bounded_capture_and_unicode() -> None:
    result = _capture((sys.executable, "-I", "-c", "print('x' * 100000)"), os.environ, 4, 100)
    assert result.outcome == "completed"
    assert len(result.stdout) == 100
    assert result.truncated
    result = _capture(
        (sys.executable, "-I", "-c", "import sys;sys.stdout.buffer.write('你好'.encode())"),
        os.environ,
        4,
    )
    assert result.stdout == "你好"


def test_missing_and_batch_rejected() -> None:
    assert CommandRunner({"PATH": ""}).run(Command.GIT_VERSION, 1).outcome == "missing"
    assert _capture(("untrusted.cmd", "&danger"), {}, 1).outcome == "blocked"


def test_relative_and_current_directory_not_resolved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ("git.exe" if os.name == "nt" else "git")).write_bytes(b"not executable")
    assert resolve_executable("git", {"PATH": str(tmp_path) + os.pathsep + "."}) is None


def test_execution_with_spaces(tmp_path: Path) -> None:
    script = tmp_path / "script with 空格.py"
    script.write_text("print('valid')", encoding="utf-8")
    assert _capture((sys.executable, "-I", str(script)), os.environ, 4).stdout.strip() == "valid"
