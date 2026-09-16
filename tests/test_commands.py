import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_dev_doctor.core.commands import (
    Command,
    CommandResult,
    CommandRunner,
    _capture,
    resolve_executable,
)


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


def test_reviewed_github_auth_command_does_not_expose_tokens() -> None:
    env = {
        "PATH": "fixture",
        "GITHUB_TOKEN": "secret-canary",
        "GH_ENTERPRISE_TOKEN": "secret-canary",
        "HTTPS_PROXY": "http://private-proxy",
        "APPDATA": "fixture-appdata",
    }
    with (
        patch("ai_dev_doctor.core.commands.resolve_executable", return_value="gh.exe"),
        patch(
            "ai_dev_doctor.core.commands._capture",
            return_value=CommandResult("completed", 0),
        ) as capture,
    ):
        CommandRunner(env).run(Command.GH_AUTH_STATUS, 1)
    argv, child_env = capture.call_args.args[:2]
    assert argv == (
        "gh.exe",
        "auth",
        "status",
        "--active",
        "--hostname",
        "github.com",
    )
    assert "--show-token" not in argv
    assert "GITHUB_TOKEN" not in child_env
    assert "GH_ENTERPRISE_TOKEN" not in child_env
    assert "HTTPS_PROXY" not in child_env
    assert child_env["GH_PROMPT_DISABLED"] == "1"
    assert child_env["GH_TELEMETRY"] == "0"


def test_npm_uses_adjacent_cli_script_not_batch_launcher(tmp_path: Path) -> None:
    node = tmp_path / "node.exe"
    script = tmp_path / "node_modules" / "npm" / "bin" / "npm-cli.js"
    script.parent.mkdir(parents=True)
    node.write_bytes(b"fixture")
    script.write_bytes(b"fixture")
    runner = CommandRunner({"PATH": str(tmp_path)})
    with (
        patch("ai_dev_doctor.core.commands.resolve_executable", return_value=str(node)),
        patch(
            "ai_dev_doctor.core.commands._capture",
            return_value=CommandResult("completed", 0, "10.0.0"),
        ) as capture,
    ):
        result = runner.run(Command.NPM_VERSION, 1)
    assert result.returncode == 0
    assert capture.call_args.args[0] == (str(node), str(script), "--version")
