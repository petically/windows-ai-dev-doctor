"""Windows system diagnostics built on the read-only inspection boundary."""

import re

from ai_dev_doctor.core.commands import Command
from ai_dev_doctor.core.engine import Context
from ai_dev_doctor.models import CheckResult, Severity, Status


def _windows(ctx: Context) -> bool:
    return ctx.host.system()[0] == "Windows"


def _version(output: str) -> str | None:
    match = re.fullmatch(r"(\d+\.\d+(?:\.\d+){0,3})\s*", output)
    return match[1] if match else None


def system_check(ctx: Context) -> CheckResult:
    system, fallback_version, machine = ctx.host.system()
    if system != "Windows":
        return CheckResult(
            "windows-system",
            "Windows system",
            "system",
            Status.SKIPPED,
            "Windows-specific check unavailable",
            evidence=(("platform", system), ("architecture", machine)),
        )
    details = ctx.windows.version()
    evidence = [("platform", system), ("architecture", machine)]
    if details is None:
        evidence.append(("version", fallback_version))
        summary = "Windows detected; edition metadata unavailable"
        status = Status.INFO
    else:
        evidence.extend(
            (
                ("edition", details.product_name),
                ("release", details.display_version),
                ("build", details.build),
            )
        )
        summary = f"{details.product_name} build {details.build} detected"
        status = Status.PASS
    return CheckResult(
        "windows-system",
        "Windows system",
        "system",
        status,
        summary,
        evidence=tuple(evidence),
        details=("Registry metadata is read only; no elevation is requested.",),
    )


def powershell_check(ctx: Context) -> CheckResult:
    if not _windows(ctx):
        return CheckResult(
            "powershell",
            "PowerShell",
            "system",
            Status.SKIPPED,
            "PowerShell check is Windows-specific",
        )
    evidence: list[tuple[str, str]] = []
    found = 0
    malformed = False
    for label, command in (
        ("Windows PowerShell", Command.POWERSHELL_VERSION),
        ("PowerShell", Command.PWSH_VERSION),
    ):
        result = ctx.runner.run(command, ctx.config.command_timeout)
        if result.outcome == "missing":
            continue
        version = (
            _version(result.stdout)
            if result.outcome == "completed" and result.returncode == 0 and not result.truncated
            else None
        )
        if version:
            found += 1
            evidence.append((label, version))
        else:
            malformed = True
            evidence.append((label, result.outcome))
    if found:
        status = Status.WARNING if malformed else Status.PASS
        summary = f"{found} PowerShell runtime{'s' if found != 1 else ''} available"
    else:
        status = Status.INFO
        summary = "PowerShell availability could not be verified through inspected PATH entries"
    return CheckResult(
        "powershell",
        "PowerShell",
        "system",
        status,
        summary,
        severity=Severity.HIGH
        if status == Status.FAIL
        else Severity.LOW
        if malformed
        else Severity.INFO,
        evidence=tuple(evidence),
        recommendations=()
        if found and not malformed
        else ("If your workflow needs PowerShell, review the inspected PATH and installation.",),
        documentation_url="https://learn.microsoft.com/powershell/",
    )


def terminal_check(ctx: Context) -> CheckResult:
    if not _windows(ctx):
        return CheckResult(
            "windows-terminal",
            "Windows Terminal",
            "system",
            Status.SKIPPED,
            "Windows Terminal discovery is Windows-specific",
        )
    state = ctx.windows.app_state("terminal")
    if state.installed:
        status, summary = Status.PASS, "Windows Terminal detected"
    elif state.installed is False:
        status, summary = (
            Status.INFO,
            "Windows Terminal not detected by inspected indicators (optional)",
        )
    else:
        status, summary = Status.INFO, "Windows Terminal detection unavailable"
    return CheckResult(
        "windows-terminal",
        "Windows Terminal",
        "system",
        status,
        summary,
        evidence=(("running", str(state.running).lower()),) if state.running is not None else (),
        severity=Severity.LOW if status == Status.WARNING else Severity.INFO,
        recommendations=(
            "Install Windows Terminal from an official Microsoft source if you want it.",
        )
        if status == Status.WARNING
        else (),
    )


def privilege_check(ctx: Context) -> CheckResult:
    if not _windows(ctx):
        return CheckResult(
            "windows-privilege",
            "User privilege",
            "system",
            Status.SKIPPED,
            "Windows privilege detection unavailable",
        )
    elevated = ctx.windows.is_admin()
    if elevated is None:
        return CheckResult(
            "windows-privilege",
            "User privilege",
            "system",
            Status.INFO,
            "Privilege state could not be determined",
        )
    return CheckResult(
        "windows-privilege",
        "User privilege",
        "system",
        Status.INFO,
        "Running elevated" if elevated else "Running as a standard user",
        evidence=(("administrator", str(elevated).lower()),),
        details=(
            "Ordinary diagnostics do not require elevation."
            if not elevated
            else "Elevated execution is unnecessary; prefer a standard-user shell.",
        ),
    )


def disk_check(ctx: Context) -> CheckResult:
    if not _windows(ctx):
        return CheckResult(
            "disk-space",
            "Disk space",
            "system",
            Status.SKIPPED,
            "Windows disk inspection unavailable",
        )
    disks = ctx.windows.disks()
    if not disks:
        return CheckResult(
            "disk-space",
            "Disk space",
            "system",
            Status.INFO,
            "Disk capacity could not be determined",
        )
    low = [disk for disk in disks if disk.free_bytes < 2 * 1024**3]
    evidence = tuple(
        (
            disk.label,
            f"{disk.free_bytes / 1024**3:.1f} GiB free of {disk.total_bytes / 1024**3:.1f} GiB",
        )
        for disk in disks
    )
    return CheckResult(
        "disk-space",
        "Disk space",
        "system",
        Status.WARNING if low else Status.PASS,
        f"{len(low)} inspected volume{'s' if len(low) != 1 else ''} below 2 GiB free"
        if low
        else "Inspected volumes have at least 2 GiB free",
        evidence=evidence,
        severity=Severity.MEDIUM if low else Severity.INFO,
        recommendations=("Free space before large builds or application updates.",) if low else (),
    )


def directories_check(ctx: Context) -> CheckResult:
    if not _windows(ctx):
        return CheckResult(
            "important-directories",
            "Important directories",
            "system",
            Status.SKIPPED,
            "Windows directory inspection unavailable",
        )
    states = ctx.windows.important_directories()
    if not states:
        return CheckResult(
            "important-directories",
            "Important directories",
            "system",
            Status.INFO,
            "Important directory metadata unavailable",
        )
    bad = [state for state in states if not state.exists or not state.readable]
    evidence = tuple(
        (
            state.label,
            "readable" if state.exists and state.readable else "missing or inaccessible",
        )
        for state in states
    )
    return CheckResult(
        "important-directories",
        "Important directories",
        "system",
        Status.WARNING if bad else Status.PASS,
        f"{len(bad)} important director{'y' if len(bad) == 1 else 'ies'} need review"
        if bad
        else "Important environment directories are readable",
        evidence=evidence,
        severity=Severity.MEDIUM if bad else Severity.INFO,
        details=("Accessibility is checked without creating temporary files.",),
    )


def webview2_check(ctx: Context) -> CheckResult:
    if not _windows(ctx):
        return CheckResult(
            "webview2-runtime",
            "WebView2 Runtime",
            "system",
            Status.SKIPPED,
            "WebView2 detection is Windows-specific",
        )
    versions = ctx.windows.webview2_versions()
    if versions is None:
        status, summary = Status.INFO, "WebView2 registry detection unavailable"
    elif versions:
        status, summary = Status.PASS, f"WebView2 Runtime {versions[-1]} detected"
    else:
        status, summary = (
            Status.INFO,
            "Evergreen WebView2 not detected; application-bundled runtimes were not inspected",
        )
    return CheckResult(
        "webview2-runtime",
        "WebView2 Runtime",
        "system",
        status,
        summary,
        evidence=tuple(("version", value) for value in versions or ()),
        severity=Severity.MEDIUM if status == Status.WARNING else Severity.INFO,
        recommendations=("Install or repair the Evergreen WebView2 Runtime manually.",)
        if status == Status.WARNING
        else (),
        documentation_url="https://developer.microsoft.com/microsoft-edge/webview2/",
    )


def gpu_check(ctx: Context) -> CheckResult:
    if not _windows(ctx):
        return CheckResult(
            "gpu-adapters",
            "GPU adapters",
            "system",
            Status.SKIPPED,
            "GPU detection is Windows-specific",
        )
    adapters = ctx.windows.gpus()
    if adapters is None:
        return CheckResult(
            "gpu-adapters",
            "GPU adapters",
            "system",
            Status.INFO,
            "GPU registry metadata unavailable",
            details=("No driver changes or DirectX commands were attempted.",),
        )
    if not adapters:
        return CheckResult(
            "gpu-adapters",
            "GPU adapters",
            "system",
            Status.INFO,
            "No GPU metadata found in the inspected registry locations",
            details=("This does not prove that no graphics adapter is present.",),
        )
    return CheckResult(
        "gpu-adapters",
        "GPU adapters",
        "system",
        Status.INFO,
        f"{len(adapters)} graphics adapter record{'s' if len(adapters) != 1 else ''} found",
        evidence=tuple(
            (gpu.name, gpu.driver_version or "driver version unavailable") for gpu in adapters
        ),
        details=(
            "Registry evidence is best effort and does not diagnose driver health or disable acceleration.",
        ),
    )


def process_check(ctx: Context) -> CheckResult:
    if not _windows(ctx):
        return CheckResult(
            "relevant-processes",
            "Relevant processes",
            "system",
            Status.SKIPPED,
            "Process inspection is Windows-specific",
        )
    names = ctx.windows.process_names()
    if names is None:
        return CheckResult(
            "relevant-processes",
            "Relevant processes",
            "system",
            Status.INFO,
            "Process enumeration unavailable",
        )
    return CheckResult(
        "relevant-processes",
        "Relevant processes",
        "system",
        Status.INFO,
        f"{len(names)} relevant process name{'s' if len(names) != 1 else ''} observed",
        evidence=tuple(("process", name) for name in names),
        details=("No command lines were read and no processes were opened or terminated.",),
    )
