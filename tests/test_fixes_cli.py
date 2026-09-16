import json
from pathlib import Path

import pytest

from ai_dev_doctor.cli import main
from ai_dev_doctor.core.engine import Context
from ai_dev_doctor.core.redaction import Redactor
from ai_dev_doctor.fixes.backup import BackupConfig, SafetyError


def test_fix_requires_confirmation_and_detects_drift(tmp_path: Path) -> None:
    source = tmp_path / "config.toml"
    source.write_text("verbose = false", encoding="utf-8")
    fix = BackupConfig(source)
    plan = fix.plan()
    assert set(tmp_path.iterdir()) == {source}
    with pytest.raises(SafetyError):
        fix.execute(plan, confirmed=False, redactor=Redactor())
    source.write_text("verbose = true", encoding="utf-8")
    with pytest.raises(SafetyError):
        fix.execute(plan, confirmed=True, redactor=Redactor())
    assert set(tmp_path.iterdir()) == {source}


def test_backup_and_audit(tmp_path: Path) -> None:
    source = tmp_path / "config.toml"
    source.write_text("verbose = false", encoding="utf-8")
    fix = BackupConfig(source)
    plan = fix.plan()
    fix.execute(plan, confirmed=True, redactor=Redactor(home=str(tmp_path)))
    assert plan.backup.read_bytes() == source.read_bytes()
    events = [json.loads(line) for line in plan.audit.read_text().splitlines()]
    assert [e["event"] for e in events] == ["fix-intent", "fix-completed"]
    assert str(tmp_path) not in plan.audit.read_text()
    with pytest.raises(SafetyError):
        fix.execute(plan, confirmed=True, redactor=Redactor())


def test_backup_collision(tmp_path: Path) -> None:
    source = tmp_path / "config.toml"
    source.write_text("", encoding="utf-8")
    fix = BackupConfig(source)
    plan = fix.plan()
    plan.backup.write_text("keep", encoding="utf-8")
    with pytest.raises(SafetyError):
        fix.execute(plan, confirmed=True, redactor=Redactor())
    assert plan.backup.read_text() == "keep"
    assert not plan.audit.exists()


def test_reject_symlink(tmp_path: Path) -> None:
    source = tmp_path / "real.toml"
    source.write_text("", encoding="utf-8")
    link = tmp_path / "config.toml"
    try:
        link.symlink_to(source)
    except OSError:
        pytest.skip("OS does not permit creating symlinks")
    with pytest.raises(SafetyError):
        BackupConfig(link).plan()


@pytest.mark.parametrize(
    "arguments",
    [
        ["help"],
        ["--help"],
        ["version"],
        ["explain", "git-version"],
        ["diagnose"],
        ["doctor"],
        ["diagnose", "--verbose"],
        ["report"],
    ],
)
def test_cli_commands(
    arguments: list[str],
    context: Context,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("ai_dev_doctor.cli.config_path", lambda: tmp_path / "absent.toml")
    assert main(arguments, context=context) == 0
    assert capsys.readouterr().out
    assert not list(tmp_path.iterdir())


def test_cli_json_export_and_log(
    context: Context,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("ai_dev_doctor.cli.config_path", lambda: tmp_path / "absent.toml")
    assert main(["diagnose", "--json"], context=context) == 0
    assert len(json.loads(capsys.readouterr().out)["results"]) == 36
    output = tmp_path / "report.html"
    log = tmp_path / "events.jsonl"
    args = ["report", "--output", str(output), "--log-file", str(log)]
    assert main(args, context=context) == 0
    assert "<!doctype html>" in output.read_text(encoding="utf-8")
    assert len(log.read_text().splitlines()) == 36
    original = output.read_bytes()
    assert main(args, context=context) == 2
    assert output.read_bytes() == original


def test_cli_dry_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "config.toml"
    source.write_text("", encoding="utf-8")
    monkeypatch.setattr("ai_dev_doctor.cli.config_path", lambda: source)
    assert main(["fix", "--dry-run", "backup-config"]) == 0
    assert "Dry run" in capsys.readouterr().out
    assert set(tmp_path.iterdir()) == {source}


def test_cli_bad_config_and_unknown_secret_arg(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "bad.toml"
    path.write_text('password = "never-echo-this"', encoding="utf-8")
    assert main(["diagnose", "--config", str(path)]) == 2
    assert "never-echo-this" not in capsys.readouterr().err
    assert main(["diagnose", "--token=arbitrary-private-value"]) == 2
    assert "arbitrary-private-value" not in capsys.readouterr().err
