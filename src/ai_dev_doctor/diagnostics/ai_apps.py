"""Best-effort ChatGPT Desktop and Codex discovery without proprietary parsing."""

from ai_dev_doctor.core.commands import Command, Tool
from ai_dev_doctor.core.engine import Context
from ai_dev_doctor.diagnostics.parsing import parse_version_token
from ai_dev_doctor.models import CheckResult, Severity, Status


def chatgpt_check(ctx: Context) -> CheckResult:
    if ctx.host.system()[0] != "Windows":
        return CheckResult(
            "chatgpt-desktop",
            "ChatGPT Desktop",
            "ai-applications",
            Status.SKIPPED,
            "ChatGPT Desktop discovery is Windows-specific",
        )
    state = ctx.windows.app_state("chatgpt")
    if state.installed or state.running:
        status = Status.INFO
        summary = "ChatGPT Desktop indicators detected"
    elif state.installed is False:
        status = Status.INFO
        summary = "ChatGPT Desktop not detected by the inspected indicators"
    else:
        status = Status.SKIPPED
        summary = "ChatGPT Desktop discovery unavailable"
    evidence: list[tuple[str, str]] = []
    if state.installed is not None:
        evidence.append(("installation-or-data", "detected" if state.installed else "not detected"))
    if state.running is not None:
        evidence.append(("running-process", "detected" if state.running else "not detected"))
    evidence.append(("data-directories", str(state.data_directories)))
    evidence.extend(
        (
            ("cache-directories", str(state.cache_directories)),
            ("cache-size", f"{state.cache_bytes / 1024**2:.1f} MiB"),
            ("cache-scan", "bounded early" if state.cache_scan_truncated else "complete"),
        )
    )
    return CheckResult(
        "chatgpt-desktop",
        "ChatGPT Desktop",
        "ai-applications",
        status,
        summary,
        evidence=tuple(evidence),
        details=(
            "Discovery combines known local application-data locations and relevant process names.",
            "Cache contents and proprietary application files are not parsed or modified.",
        ),
        recommendations=(
            "Use Windows Apps settings to repair or reinstall ChatGPT if symptoms persist.",
        )
        if state.installed and not state.running
        else (),
    )


def codex_cli_check(ctx: Context) -> CheckResult:
    locations = ctx.runner.locations(Tool.CODEX)
    result = ctx.runner.run(Command.CODEX_VERSION, ctx.config.command_timeout)
    version = (
        parse_version_token(result.stdout)
        if result.outcome == "completed" and result.returncode == 0 and not result.truncated
        else None
    )
    evidence: list[tuple[str, str]] = [("outcome", result.outcome)]
    if result.executable:
        evidence.append(("probe-executable", result.executable))
    if locations:
        evidence.append(("path-matches", str(len(locations))))
    if version:
        status, summary = Status.PASS, f"Codex CLI {version} is executable"
        evidence.append(("version", version))
    elif result.outcome == "missing":
        status, summary = Status.WARNING, "Codex CLI not found on inspected local PATH entries"
    elif result.outcome == "blocked":
        status, summary = Status.WARNING, "Codex CLI found only through an unsafe batch launcher"
    else:
        status, summary = Status.WARNING, "Codex CLI version probe could not complete reliably"
    return CheckResult(
        "codex-cli",
        "Codex CLI",
        "ai-applications",
        status,
        summary,
        severity=Severity.LOW if status == Status.WARNING else Severity.INFO,
        evidence=tuple(evidence),
        details=("No Codex command that reads authentication or connects to a service is run.",),
        recommendations=("Review the Codex installation and PATH ordering.",)
        if status == Status.WARNING
        else (),
    )


def codex_environment_check(ctx: Context) -> CheckResult:
    if ctx.host.system()[0] != "Windows":
        return CheckResult(
            "codex-environment",
            "Codex environment",
            "ai-applications",
            Status.SKIPPED,
            "Codex environment discovery is Windows-specific",
        )
    state = ctx.windows.app_state("codex")
    if state.installed:
        status, summary = Status.INFO, "Codex configuration directory detected"
    elif state.installed is False:
        status, summary = Status.INFO, "Codex configuration directory not detected"
    else:
        status, summary = Status.SKIPPED, "Codex configuration discovery unavailable"
    if state.config_readable is False:
        status, summary = Status.WARNING, "Codex configuration exists but is not readable"
    evidence: list[tuple[str, str]] = [
        ("configuration-directory", "detected" if state.installed else "not detected"),
    ]
    if state.config_readable is not None:
        evidence.append(("config.toml", "readable" if state.config_readable else "not readable"))
    if state.running is not None:
        evidence.append(("running-process", "detected" if state.running else "not detected"))
    return CheckResult(
        "codex-environment",
        "Codex environment",
        "ai-applications",
        status,
        summary,
        evidence=tuple(evidence),
        severity=Severity.MEDIUM if status == Status.WARNING else Severity.INFO,
        details=(
            "Only directory and file metadata are inspected; configuration contents and credentials are not read.",
        ),
        recommendations=("Review file permissions on the Codex configuration.",)
        if status == Status.WARNING
        else (),
    )
