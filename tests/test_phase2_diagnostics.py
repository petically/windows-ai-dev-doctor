from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import cast

# Phase 2 fakes are intentionally local to exercise the full adapter contracts.
from ai_dev_doctor.core.commands import Command, CommandResult, Executable, Tool
from ai_dev_doctor.core.engine import Context
from ai_dev_doctor.core.windows import (
    AdapterState,
    AppState,
    DirectoryState,
    DiskState,
    GPUState,
    ListenerState,
    ProxyState,
    WindowsVersion,
    _cache_metadata,
)
from ai_dev_doctor.diagnostics.ai_apps import (
    chatgpt_check,
    codex_cli_check,
    codex_environment_check,
)
from ai_dev_doctor.diagnostics.developer_tools import (
    git_config_check,
    git_repository_check,
    github_auth_check,
    node_check,
    python_check,
)
from ai_dev_doctor.diagnostics.environment import (
    developer_environment_check,
    executable_shadowing_check,
)
from ai_dev_doctor.diagnostics.network import (
    adapter_check,
    listener_check,
    proxy_layers_check,
    system_proxy_check,
)
from ai_dev_doctor.diagnostics.parsing import (
    parse_git_status,
    parse_version_token,
    parse_windows_proxy,
)
from ai_dev_doctor.diagnostics.system import (
    directories_check,
    disk_check,
    gpu_check,
    system_check,
    webview2_check,
)
from ai_dev_doctor.models import Status


@dataclass
class DetailedRunner:
    results: dict[Command, CommandResult] = field(default_factory=dict)
    found: dict[Tool, tuple[Executable, ...]] = field(default_factory=dict)

    def run(self, command: Command, timeout: float) -> CommandResult:
        return self.results.get(command, CommandResult("missing"))

    def locations(self, tool: Tool) -> tuple[Executable, ...]:
        return self.found.get(tool, ())


@dataclass
class FakeWindows:
    available: bool = True
    version_value: WindowsVersion | None = WindowsVersion("Windows 11 Pro", "24H2", "26100.1")
    admin: bool | None = False
    directory_values: tuple[DirectoryState, ...] = (
        DirectoryState("temporary", r"C:\Temp", True, True),
    )
    disk_values: tuple[DiskState, ...] = (DiskState("system", 10 * 1024**3, 100 * 1024**3),)
    webview_values: tuple[str, ...] | None = ("131.0.0.0",)
    system_proxy_value: ProxyState = ProxyState("ok")
    winhttp_proxy_value: ProxyState = ProxyState("ok")
    adapter_values: tuple[AdapterState, ...] | None = (AdapterState(7, "ethernet", False),)
    route: int | None = 7
    listener_values: tuple[ListenerState, ...] | None = ()
    process_values: tuple[str, ...] | None = ("python.exe",)
    gpu_values: tuple[GPUState, ...] | None = (GPUState("Fixture GPU", "1.2.3"),)
    apps: dict[str, AppState] = field(
        default_factory=lambda: {
            "chatgpt": AppState(True, False, 1),
            "codex": AppState(True, True, 1, True),
            "terminal": AppState(True, False),
        }
    )

    def version(self) -> WindowsVersion | None:
        return self.version_value

    def is_admin(self) -> bool | None:
        return self.admin

    def important_directories(self) -> tuple[DirectoryState, ...]:
        return self.directory_values

    def disks(self) -> tuple[DiskState, ...]:
        return self.disk_values

    def webview2_versions(self) -> tuple[str, ...] | None:
        return self.webview_values

    def system_proxy(self) -> ProxyState:
        return self.system_proxy_value

    def winhttp_proxy(self) -> ProxyState:
        return self.winhttp_proxy_value

    def adapters(self) -> tuple[AdapterState, ...] | None:
        return self.adapter_values

    def default_route_interface(self) -> int | None:
        return self.route

    def listeners(self, ports: tuple[int, ...]) -> tuple[ListenerState, ...] | None:
        return tuple(item for item in self.listener_values or () if item.port in ports)

    def process_names(self) -> tuple[str, ...] | None:
        return self.process_values

    def gpus(self) -> tuple[GPUState, ...] | None:
        return self.gpu_values

    def app_state(self, app: str) -> AppState:
        return self.apps.get(app, AppState(None, None))


def phase2_context(context: Context) -> Context:
    return replace(context, runner=DetailedRunner(), windows=FakeWindows())


def test_new_parsers_are_minimal_and_strict() -> None:
    assert parse_version_token("gh version 2.80.1 (fixture)") == "2.80.1"
    assert parse_version_token("unparseable") is None
    clean = parse_git_status("# branch.oid abc\n1 .M N... 100644 100644 100644 a b file")
    assert clean is not None and clean.tracked_changes == 1 and clean.conflicts == 0
    conflict = parse_git_status("u UU N... 100644 100644 100644 100644 a b c file")
    assert conflict is not None and conflict.conflicts == 1
    assert parse_git_status("private unexpected output") is None
    endpoints = parse_windows_proxy("http=127.0.0.1:8080;https=proxy.example:443")
    assert endpoints is not None and [item.port for item in endpoints] == [8080, 443]
    assert parse_windows_proxy("unknown=private:1") is None


def test_windows_system_branches(context: Context) -> None:
    ctx = phase2_context(context)
    assert system_check(ctx).status == Status.PASS
    assert webview2_check(ctx).status == Status.PASS
    assert gpu_check(ctx).status == Status.INFO

    windows = cast(FakeWindows, ctx.windows)
    low = replace(windows, disk_values=(DiskState("system", 1, 100),))
    assert disk_check(replace(ctx, windows=low)).status == Status.WARNING
    denied = replace(
        windows,
        directory_values=(DirectoryState("temporary", r"C:\Temp", True, False),),
    )
    assert directories_check(replace(ctx, windows=denied)).status == Status.WARNING
    missing_webview = replace(windows, webview_values=())
    assert webview2_check(replace(ctx, windows=missing_webview)).status == Status.WARNING


def test_developer_tool_results_and_repository_privacy(context: Context) -> None:
    runner = DetailedRunner(
        results={
            Command.GIT_IDENTITY_KEYS: CommandResult("completed", 0, "user.name\nuser.email\n"),
            Command.GIT_DEFAULT_BRANCH: CommandResult("completed", 0, "main\n"),
            Command.GIT_CREDENTIAL_HELPER_KEYS: CommandResult(
                "completed", 0, "credential.helper\n"
            ),
            Command.GIT_REPOSITORY: CommandResult(
                "completed", 0, "# branch.oid secret\nu UU N... 1 1 1 1 a b c private.txt\n"
            ),
            Command.GH_AUTH_STATUS: CommandResult("completed", 1),
            Command.PYTHON_VERSION: CommandResult("completed", 0, "Python 3.12.10"),
            Command.NODE_VERSION: CommandResult("completed", 0, "v22.11.0"),
        },
        found={
            Tool.GIT: (Executable(r"C:\Git\git.exe", True),),
            Tool.GH: (Executable(r"C:\GitHub\gh.exe", True),),
            Tool.PYTHON: (
                Executable(r"C:\Python312\python.exe", True),
                Executable(r"C:\Python313\python.exe", True),
            ),
            Tool.NODE: (Executable(r"C:\Node\node.exe", True),),
        },
    )
    ctx = replace(phase2_context(context), runner=runner)
    assert git_config_check(ctx).status == Status.PASS
    repository = git_repository_check(ctx)
    assert repository.status == Status.WARNING
    assert "private.txt" not in str(repository)
    assert github_auth_check(ctx).status == Status.WARNING
    assert python_check(ctx).status == Status.PASS
    assert "multiple installations" in " ".join(python_check(ctx).details)
    assert node_check(ctx).status == Status.PASS


def test_environment_and_shadowing_are_conservative(context: Context) -> None:
    host = replace(  # type: ignore[type-var]
        context.host,
        environment={
            "PATH": r"C:\Tools",
            "VIRTUAL_ENV": r"C:\Missing",
            "OPENAI_API_KEY": "secret-canary",
        },
    )
    runner = DetailedRunner(
        found={
            Tool.PYTHON: (
                Executable(r"C:\first\python.cmd", False),
                Executable(r"C:\second\python.exe", True),
            )
        }
    )
    ctx = replace(phase2_context(context), host=host, runner=runner)
    environment = developer_environment_check(ctx)
    assert environment.status == Status.WARNING
    assert "secret-canary" not in str(environment)
    shadowing = executable_shadowing_check(ctx)
    assert shadowing.status == Status.WARNING
    assert "multiple installations" in " ".join(shadowing.details).lower()


def test_network_layers_require_corroborating_evidence(context: Context) -> None:
    windows = replace(
        cast(FakeWindows, phase2_context(context).windows),
        system_proxy_value=ProxyState("ok", True, "127.0.0.1:7890"),
        adapter_values=(AdapterState(7, "tunnel", True),),
        listener_values=(),
    )
    ctx = replace(phase2_context(context), windows=windows)
    assert system_proxy_check(ctx).status == Status.INFO
    assert adapter_check(ctx).status == Status.PASS
    conflict = proxy_layers_check(ctx)
    assert conflict.status == Status.WARNING
    assert "Possible conflict" in conflict.summary

    listening = replace(windows, listener_values=(ListenerState(7890, 42),))
    healthy = proxy_layers_check(replace(ctx, windows=listening))
    assert healthy.status == Status.INFO
    assert listener_check(replace(ctx, windows=listening)).status == Status.INFO


def test_ai_application_discovery_is_informational(context: Context) -> None:
    runner = DetailedRunner(
        results={Command.CODEX_VERSION: CommandResult("completed", 0, "codex-cli 0.50.0")},
        found={Tool.CODEX: (Executable(r"C:\Tools\codex.exe", True),)},
    )
    ctx = replace(phase2_context(context), runner=runner)
    assert chatgpt_check(ctx).status == Status.INFO
    assert codex_cli_check(ctx).status == Status.PASS
    assert codex_environment_check(ctx).status == Status.INFO


def test_cache_metadata_scan_is_bounded(tmp_path: Path, context: Context) -> None:
    ctx = phase2_context(context)
    cache = tmp_path / "GPUCache"
    cache.mkdir()
    (cache / "entry.bin").write_bytes(b"x" * 32)
    directories, size, truncated = _cache_metadata((tmp_path,))
    assert (directories, size, truncated) == (1, 32, False)
    _, _, truncated = _cache_metadata((tmp_path,), limit=0)
    assert truncated
    assert "contents" in codex_environment_check(ctx).details[0]
