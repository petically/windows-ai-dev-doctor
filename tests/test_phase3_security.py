import ctypes
import io
import os
import socket
import struct
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import TextIO
from unittest.mock import MagicMock, patch

import pytest
from test_phase2_diagnostics import DetailedRunner, FakeWindows

from ai_dev_doctor.core.commands import Command, CommandResult, Executable, Tool, _capture
from ai_dev_doctor.core.engine import Context
from ai_dev_doctor.core.logging import write_event
from ai_dev_doctor.core.network import _perform
from ai_dev_doctor.core.redaction import Redactor
from ai_dev_doctor.core.windows import LocalWindowsInspector, ProxyState, _parse_tcp_table
from ai_dev_doctor.diagnostics.ai_apps import codex_cli_check
from ai_dev_doctor.diagnostics.developer_tools import git_config_check, github_cli_check
from ai_dev_doctor.diagnostics.network import adapter_check, proxy_layers_check
from ai_dev_doctor.models import CheckResult, Status
from ai_dev_doctor.reporting import render_html, render_json, render_terminal


@pytest.mark.parametrize("parent_wait", [True, False])
def test_owned_descendants_die_and_unrelated_process_survives(parent_wait: bool) -> None:
    unrelated = subprocess.Popen([sys.executable, "-I", "-c", "import time; time.sleep(30)"])
    try:
        script = (
            "import subprocess,sys,time; "
            'p=subprocess.Popen([sys.executable,"-I","-c","import time; time.sleep(30)"]); '
            "print(p.pid,flush=True); " + ("time.sleep(30)" if parent_wait else "time.sleep(0.1)")
        )
        started = time.monotonic()
        result = _capture((sys.executable, "-I", "-c", script), os.environ, 2)
        assert result.outcome == ("timeout" if parent_wait else "completed")
        assert time.monotonic() - started < 6
        pid = int(result.stdout.strip())
        if sys.platform == "win32":
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenProcess.argtypes = (ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong)
            kernel.OpenProcess.restype = ctypes.c_void_p
            kernel.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_ulong)
            kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
            handle = kernel.OpenProcess(0x100000, False, pid)
            if handle:
                try:
                    assert kernel.WaitForSingleObject(handle, 2000) == 0
                finally:
                    kernel.CloseHandle(handle)
        else:
            status = Path(f"/proc/{pid}/stat")
            try:
                state = status.read_text().split()[2]
            except FileNotFoundError:
                state = "gone"  # The OS may reap it between observation and read.
            assert state in ("Z", "gone")
        assert unrelated.poll() is None
    finally:
        unrelated.terminate()
        unrelated.wait(timeout=5)


def test_stderr_flood_and_invalid_utf8_are_bounded() -> None:
    result = _capture(
        (
            sys.executable,
            "-I",
            "-c",
            "import sys;sys.stderr.buffer.write(b'x'*1000000);sys.stdout.buffer.write(b'\\xffok')",
        ),
        os.environ,
        4,
    )
    assert result.outcome == "completed"
    assert result.stdout == "\ufffdok"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows job enforcement")
def test_failed_job_setup_never_starts_command(tmp_path: Path) -> None:
    fake = MagicMock()
    fake.CreateJobObjectW.return_value = 123
    fake.SetInformationJobObject.return_value = 0
    with patch("ctypes.WinDLL", return_value=fake):
        result = _capture((sys.executable, "-I", "-c", "raise SystemExit(99)"), os.environ, 1)
    assert result.outcome == "unavailable"
    fake.CreateProcessW.assert_not_called()
    fake.CloseHandle.assert_called_with(123)


@pytest.mark.parametrize(
    "text,canary",
    [
        ('{"PaSsWoRd": "first\\"private-canary"}', "private-canary"),
        ("api_key: |\n  private-canary\n  second-line", "private-canary"),
        ("Authorization: Basic abc\n  private-canary", "private-canary"),
        ("Server=local;UID=private-canary;PWD=private-password", "private-canary"),
        ("Server=local;Uid=test;Pwd=private-canary", "private-canary"),
        ("postgresql://user:private-canary@db.invalid/db", "private-canary"),
        ("ssh://user:private-canary@host/repo", "private-canary"),
        ("https://example.com/#private-canary", "private-canary"),
        ("Session_ID = private-canary", "private-canary"),
        ('ACCESS_KEY="private-canary"', "private-canary"),
        (
            "-----BEGIN PRIVATE KEY-----\nprivate-canary\n-----END PRIVATE KEY-----",
            "private-canary",
        ),
        (r"D:\OtherUser\private-canary\project", "private-canary"),
        (r"\\private-canary\share\document", "private-canary"),
        ("/home/private-canary/project", "private-canary"),
    ],
)
def test_expanded_privacy_corpus_across_every_surface(text: str, canary: str) -> None:
    result = CheckResult(
        "privacy",
        text,
        "system",
        Status.INFO,
        text,
        details=(text,),
        evidence=(("detail", text),),
        recommendations=(text,),
    )
    redactor = Redactor()
    log = io.StringIO()
    write_event(log, redactor, "test", detail=text)
    for output in (
        render_json((result,), redactor),
        render_html((result,), redactor),
        render_terminal((result,), redactor, verbose=True),
        log.getvalue(),
    ):
        assert canary not in output


@pytest.mark.parametrize(
    "data", [b"", b"\x01", struct.pack("<I", 1), struct.pack("<I", 0xFFFFFFFF)]
)
def test_malformed_tcp_table_never_reads_out_of_bounds(data: bytes) -> None:
    assert _parse_tcp_table(data, (8080,)) is None


def test_tcp_table_excludes_nonlocal_and_nonlistening_rows() -> None:
    rows = b"".join(
        struct.pack("<6I", state, address, socket.htons(8080), 0, 0, pid)
        for state, address, pid in (
            (2, 0, 10),
            (2, 0x0100007F, 11),
            (2, 0x0100000A, 12),
            (5, 0, 13),
        )
    )
    values = _parse_tcp_table(struct.pack("<I", 4) + rows, (8080,))
    assert values is not None and [v.pid for v in values] == [10, 11]


@pytest.mark.parametrize(
    "server,enabled", [("127.0.0.1:7890", False), ("[::1]:7890", True), ("localhost:7890", True)]
)
def test_inactive_or_uninspected_proxy_is_not_a_conflict(
    context: Context, server: str, enabled: bool
) -> None:
    windows = FakeWindows(system_proxy_value=ProxyState("ok", enabled, server))
    result = proxy_layers_check(replace(context, windows=windows))
    assert result.status == Status.INFO
    assert not result.recommendations


def test_unavailable_ipv4_reference_route_does_not_prove_outage(context: Context) -> None:
    result = adapter_check(replace(context, windows=FakeWindows(route=None)))
    assert result.status == Status.INFO


def test_optional_tools_do_not_require_installation(context: Context) -> None:
    ctx = replace(context, runner=DetailedRunner())
    assert github_cli_check(ctx).status == Status.INFO
    assert codex_cli_check(ctx).status == Status.INFO


def test_git_config_error_is_not_reported_as_missing_identity(context: Context) -> None:
    runner = DetailedRunner(
        results={
            command: CommandResult("completed", 128)
            for command in (
                Command.GIT_IDENTITY_KEYS,
                Command.GIT_DEFAULT_BRANCH,
                Command.GIT_CREDENTIAL_HELPER_KEYS,
            )
        },
        found={Tool.GIT: (Executable("git", True),)},
    )
    result = git_config_check(replace(context, runner=runner))
    assert "reliably" in result.summary
    assert not result.recommendations


@pytest.mark.skipif(sys.platform != "win32", reason="Windows metadata adapter")
def test_missing_optional_codex_config_and_unknown_process_state(tmp_path: Path) -> None:
    (tmp_path / ".codex").mkdir()
    inspector = LocalWindowsInspector({"USERPROFILE": str(tmp_path)})
    with patch.object(inspector, "process_names", return_value=None):
        state = inspector.app_state("codex")
    assert state.installed and state.config_readable is None and state.running is None


def test_empty_dns_answer_is_not_pass() -> None:
    with patch("socket.getaddrinfo", return_value=[]):
        assert not _perform("dns", "example.com", 1).ok


def test_no_raw_private_command_output_reaches_diagnostics(context: Context) -> None:
    runner = DetailedRunner(
        results={Command.CODEX_VERSION: CommandResult("completed", 1, "private-canary")}
    )
    assert "private-canary" not in str(codex_cli_check(replace(context, runner=runner)))


@pytest.mark.parametrize("kind", ["triple-double", "triple-single"])
def test_toml_multiline_secret(kind: str) -> None:
    quote = '"' * 3 if kind == "triple-double" else "'" * 3
    text = "api_key = " + quote + "\nprivate-canary\n" + quote
    assert "private-canary" not in Redactor().text(text)


def test_misleading_version_text_is_not_pass(context: Context) -> None:
    runner = DetailedRunner(
        results={Command.CODEX_VERSION: CommandResult("completed", 0, "Error loading config 1.2.3")}
    )
    assert codex_cli_check(replace(context, runner=runner)).status != Status.PASS


def test_cancellation_closes_owned_process() -> None:
    proc = MagicMock()
    proc.stdout = io.BytesIO()
    proc.stderr = io.BytesIO()
    proc.wait.side_effect = KeyboardInterrupt
    with (
        patch("ai_dev_doctor.core.commands.start_process", return_value=proc),
        pytest.raises(KeyboardInterrupt),
    ):
        _capture((sys.executable,), {}, 1)
    proc.close.assert_called_once()


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 ABI")
def test_windows_job_structure_layouts() -> None:
    from ai_dev_doctor.core.process import (
        _BasicLimits,
        _ExtendedLimits,
        _StartupInfo,
        _StartupInfoEx,
    )

    if ctypes.sizeof(ctypes.c_void_p) == 8:
        assert ctypes.sizeof(_BasicLimits) == 64
        assert ctypes.sizeof(_ExtendedLimits) == 144
        assert ctypes.sizeof(_StartupInfo) == 104
        assert ctypes.sizeof(_StartupInfoEx) == 112
        assert _StartupInfo.hStdInput.offset == 80


def test_fix_revalidates_after_audit_and_preserves_original(tmp_path: Path) -> None:
    from ai_dev_doctor.fixes.backup import BackupConfig, SafetyError

    source = tmp_path / "config.toml"
    source.write_text("verbose = false", encoding="utf-8")
    fix = BackupConfig(source)
    plan = fix.plan()
    original_write = write_event

    def drifting_log(stream: TextIO, redactor: Redactor, event: str, **fields: object) -> None:
        original_write(stream, redactor, event, **fields)
        if event == "fix-intent":
            source.write_text("verbose = true", encoding="utf-8")

    with (
        patch("ai_dev_doctor.fixes.backup.write_event", side_effect=drifting_log),
        pytest.raises(SafetyError),
    ):
        fix.execute(plan, confirmed=True, redactor=Redactor())
    assert not plan.backup.exists()
    assert source.read_text() == "verbose = true"
    assert "fix-failed" in plan.audit.read_text()


def test_cli_redirected_output_is_utf8_under_legacy_encoding(tmp_path: Path) -> None:
    # Exercise the real entry point under the encoding used by older Windows shells.
    environment = dict(os.environ)
    environment["PYTHONIOENCODING"] = "cp1252"
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    config = tmp_path / "config.toml"
    config.write_text("enabled_categories = []", encoding="utf-8")
    destination = tmp_path / ("report-" + chr(0x6D4B) + ".json")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ai_dev_doctor",
            "report",
            "--config",
            str(config),
            "--output",
            str(destination),
        ],
        env=environment,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0 and not result.stderr
    output = result.stdout.decode("utf-8", errors="strict")
    assert "Report created:" in output
    assert destination.is_file()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows metadata adapter")
def test_application_access_denied_stays_unknown() -> None:
    inspector = LocalWindowsInspector({})
    with patch.object(inspector, "_app_state", side_effect=PermissionError):
        state = inspector.app_state("chatgpt")
    assert state.installed is None and state.running is None


def test_uninspected_cache_roots_do_not_claim_complete(tmp_path: Path) -> None:
    from ai_dev_doctor.core.windows import _cache_metadata

    with patch("ai_dev_doctor.core.windows.is_local_path", return_value=False):
        assert _cache_metadata((tmp_path,)) == (0, 0, True)
