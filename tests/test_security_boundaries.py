import io
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_dev_doctor.cli import main
from ai_dev_doctor.core.commands import Command, CommandResult, CommandRunner
from ai_dev_doctor.core.redaction import Redactor
from ai_dev_doctor.core.safety import validate_fix_path
from ai_dev_doctor.fixes.backup import BackupConfig, SafetyError
from ai_dev_doctor.models import CheckResult, Status
from ai_dev_doctor.reporting import render_html, render_json, render_terminal


def test_sensitive_evidence_keys() -> None:
    result = CheckResult(
        "canary",
        "Privacy",
        "system",
        Status.INFO,
        "Fixture",
        evidence=(("api_key", "unstructured-canary"),),
    )
    redactor = Redactor()
    for content in (
        render_json((result,), redactor),
        render_html((result,), redactor),
        render_terminal((result,), redactor, verbose=True),
    ):
        assert "unstructured-canary" not in content


def test_credentials_not_inherited_by_commands() -> None:
    env = {
        "PATH": "fixture",
        "OPENAI_API_KEY": "canary",
        "GITHUB_TOKEN": "canary",
        "HTTP_PROXY": "http://private@host",
        "SYSTEMROOT": "fixture",
    }
    with (
        patch("ai_dev_doctor.core.commands.resolve_executable", return_value="git.exe"),
        patch(
            "ai_dev_doctor.core.commands._capture", return_value=CommandResult("completed")
        ) as capture,
    ):
        CommandRunner(env).run(Command.GIT_VERSION, 1)
    child_env = capture.call_args.args[1]
    assert "OPENAI_API_KEY" not in child_env
    assert "GITHUB_TOKEN" not in child_env
    assert "HTTP_PROXY" not in child_env


def test_audit_failure_prevents_backup(tmp_path: Path) -> None:
    source = tmp_path / "config.toml"
    source.write_text("", encoding="utf-8")
    fix = BackupConfig(source)
    plan = fix.plan()
    with (
        patch("ai_dev_doctor.fixes.backup.write_event", side_effect=OSError("full disk")),
        pytest.raises(OSError),
    ):
        fix.execute(plan, confirmed=True, redactor=Redactor())
    assert not plan.backup.exists()
    assert source.read_bytes() == b""


def test_completion_audit_failure_preserves_backup(tmp_path: Path) -> None:
    source = tmp_path / "config.toml"
    source.write_text("", encoding="utf-8")
    fix = BackupConfig(source)
    plan = fix.plan()
    with (
        patch("ai_dev_doctor.fixes.backup.write_event", side_effect=[None, OSError("full disk")]),
        pytest.raises(SafetyError, match="Backup created"),
    ):
        fix.execute(plan, confirmed=True, redactor=Redactor())
    assert plan.backup.exists()


def test_forged_plan_rejected(tmp_path: Path) -> None:
    source = tmp_path / "config.toml"
    source.write_text("", encoding="utf-8")
    fix = BackupConfig(source)
    plan = replace(fix.plan(), backup=tmp_path.parent / "elsewhere.bak")
    with pytest.raises(SafetyError):
        fix.execute(plan, confirmed=True, redactor=Redactor())


def test_reparse_attribute_rejected_without_symlink_privilege(tmp_path: Path) -> None:
    source = tmp_path / "config.toml"
    source.write_text("", encoding="utf-8")

    class Reparse:
        st_mode = 0o100600
        st_file_attributes = 0x400

    with patch.object(Path, "lstat", return_value=Reparse()), pytest.raises(SafetyError):
        validate_fix_path(source, file_required=True)


def test_noninteractive_fix_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "config.toml"
    source.write_text("", encoding="utf-8")
    monkeypatch.setattr("ai_dev_doctor.cli.config_path", lambda: source)
    monkeypatch.setattr("sys.stdin", io.StringIO("yes\n"))
    assert main(["fix", "backup-config"]) == 2
    assert set(tmp_path.iterdir()) == {source}


@pytest.mark.parametrize("answer,created", [("no", False), ("", False), ("yes", True)])
def test_interactive_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answer: str, created: bool
) -> None:
    source = tmp_path / "config.toml"
    source.write_text("", encoding="utf-8")
    monkeypatch.setattr("ai_dev_doctor.cli.config_path", lambda: source)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: answer)
    assert main(["fix", "backup-config"]) == 0
    assert bool(list(tmp_path.glob("*.bak"))) == created


def test_control_only_text_does_not_break_renderers() -> None:
    result = CheckResult("control", "Demo", "system", Status.INFO, chr(27) + "[31m")
    assert "[empty]" in render_json((result,), Redactor())
