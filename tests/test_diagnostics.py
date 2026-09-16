from dataclasses import replace

import pytest
from conftest import FakeHost, FakeNetwork, FakeRunner

from ai_dev_doctor.core.commands import CommandResult
from ai_dev_doctor.core.engine import Context
from ai_dev_doctor.diagnostics.builtin import git_check, path_check, proxy_check, registry
from ai_dev_doctor.diagnostics.parsing import analyze_path, parse_git_version, parse_proxy
from ai_dev_doctor.models import Status


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("git version 2.50.1.windows.1\n", "2.50.1.windows.1"),
        ("git version 2.49.0", "2.49.0"),
        ("malformed", None),
        ("git version 2.50.0\npassword=leak", None),
    ],
)
def test_version_parser(raw: str, expected: str | None) -> None:
    assert parse_git_version(raw) == expected


def test_windows_path_semantics() -> None:
    value = 'C:\\Tools;c:\\tools\\;"C:\\Other";relative;;C:\\不存在'
    findings = analyze_path(value, lambda p: p.lower().rstrip("\\") == r"c:\tools")
    kinds = [k for k, _ in findings]
    assert kinds.count("duplicate") == 1
    assert {"quoting", "relative", "empty", "missing"} <= set(kinds)


@pytest.mark.parametrize(
    "value,valid",
    [
        ("http://user:password@127.0.0.1:8080", True),
        ("localhost:7890", True),
        ("socks5://[::1]:1080", True),
        ("http://host:99999", False),
        ("https://", False),
        ("ftp://host", False),
        ("http://host/path", False),
    ],
)
def test_proxy_parser(value: str, valid: bool) -> None:
    assert (parse_proxy(value) is not None) == valid


def test_proxy_is_not_automatically_failure(context: Context) -> None:
    host = FakeHost(
        {"HTTP_PROXY": "http://user:super-private@localhost:7890", "NO_PROXY": "internal.company"}
    )
    result = proxy_check(replace(context, host=host))
    assert result.status == Status.INFO
    assert "super-private" not in str(result)
    assert "internal.company" not in str(result)


@pytest.mark.parametrize(
    "result",
    [
        CommandResult("missing"),
        CommandResult("timeout"),
        CommandResult("completed", 1),
        CommandResult("completed", 0, "unexpected"),
    ],
)
def test_git_failures(context: Context, result: CommandResult) -> None:
    assert git_check(replace(context, runner=FakeRunner(result))).status == Status.WARNING


def test_path_platform_guard(context: Context) -> None:
    assert path_check(replace(context, host=FakeHost(platform="Linux"))).status == Status.SKIPPED


def test_network_opt_in_and_multiple_targets(context: Context) -> None:
    network = FakeNetwork()
    context = replace(context, network=network)
    registry().run(context)
    assert not network.calls
    results = registry().run(replace(context, network_allowed=True), "network")
    assert len(network.calls) == 6
    assert results[-1].status == Status.PASS
    network.ok = False
    assert registry().run(replace(context, network_allowed=True))[-1].status == Status.FAIL


def test_remote_path_does_not_touch_filesystem() -> None:
    def forbidden(path: str) -> bool:
        raise AssertionError("UNC lookup must not occur")

    findings = analyze_path(r"\\\\server\\share", forbidden)
    assert findings[0][0] == "uninspected"


def test_zero_proxy_port_is_invalid() -> None:
    assert parse_proxy("http://localhost:0") is None
