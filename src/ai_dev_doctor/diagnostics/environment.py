"""PATH and developer-environment diagnostics."""

import ntpath

from ai_dev_doctor.core.commands import Tool
from ai_dev_doctor.core.engine import Context
from ai_dev_doctor.diagnostics.parsing import analyze_path
from ai_dev_doctor.models import CheckResult, Severity, Status


def path_check(ctx: Context) -> CheckResult:
    if ctx.host.system()[0] != "Windows":
        return CheckResult(
            "path-structure",
            "PATH structure",
            "environment",
            Status.SKIPPED,
            "Windows PATH analysis is unavailable on this platform",
        )
    value = ctx.host.environment.get("PATH", "")
    findings = analyze_path(value, ctx.host.directory_exists)
    counts: dict[str, int] = {}
    for kind, _ in findings:
        counts[kind] = counts.get(kind, 0) + 1
    evidence = tuple((kind, str(count)) for kind, count in sorted(counts.items()))
    return CheckResult(
        "path-structure",
        "PATH structure",
        "environment",
        Status.WARNING
        if any(k != "uninspected" for k, _ in findings)
        else Status.INFO
        if findings
        else Status.PASS,
        f"{len(findings)} PATH structural finding{'s' if len(findings) != 1 else ''}"
        if findings
        else "PATH directories exist without structural issues",
        evidence=evidence,
        details=(
            "Individual PATH values are omitted; use verbose local inspection if you need to identify entries.",
        )
        if findings
        else (),
        severity=Severity.LOW if findings else Severity.INFO,
        recommendations=("Review entries manually; no PATH changes were made.",)
        if findings
        else (),
    )


def developer_environment_check(ctx: Context) -> CheckResult:
    if ctx.host.system()[0] != "Windows":
        return CheckResult(
            "developer-environment",
            "Developer environment",
            "environment",
            Status.SKIPPED,
            "Windows developer-environment analysis is unavailable",
        )
    path_variables = (
        "VIRTUAL_ENV",
        "CONDA_PREFIX",
        "PYENV_ROOT",
        "NVM_HOME",
        "NVM_SYMLINK",
        "FNM_DIR",
        "NODE_PATH",
        "JAVA_HOME",
        "GOPATH",
        "CARGO_HOME",
    )
    evidence: list[tuple[str, str]] = []
    bad: list[str] = []
    for key in path_variables:
        raw = ctx.host.environment.get(key)
        if not raw:
            continue
        values = raw.split(";") if key in ("NODE_PATH", "GOPATH") else [raw]
        statuses = []
        for value in values[:32]:
            cleaned = value.strip().strip('"')
            if not ntpath.isabs(cleaned):
                statuses.append("relative")
                bad.append(key)
                continue
            exists = ctx.host.directory_exists(cleaned)
            if exists is True:
                statuses.append("exists")
            elif exists is False:
                statuses.append("missing")
                bad.append(key)
            else:
                statuses.append("not-inspected")
        evidence.append((key, ", ".join(statuses)))
    return CheckResult(
        "developer-environment",
        "Developer environment",
        "environment",
        Status.WARNING if bad else Status.INFO,
        f"{len(set(bad))} configured developer path variable{'s' if len(set(bad)) != 1 else ''} need review"
        if bad
        else (
            "Configured developer path variables inspected where accessible"
            if evidence
            else "No supported developer path variables are configured"
        ),
        evidence=tuple(evidence),
        severity=Severity.LOW if bad else Severity.INFO,
        details=("Variable values are deliberately omitted from evidence.",),
        recommendations=("Review missing or relative developer path variables manually.",)
        if bad
        else (),
    )


def executable_shadowing_check(ctx: Context) -> CheckResult:
    tools = (Tool.GIT, Tool.GH, Tool.PYTHON, Tool.NODE, Tool.CODEX)
    evidence: list[tuple[str, str]] = []
    multiple: list[str] = []
    unsafe_first: list[str] = []
    for tool in tools:
        locations = ctx.runner.locations(tool)
        if not locations:
            continue
        evidence.append(
            (tool.value, f"{len(locations)} local PATH match{'es' if len(locations) != 1 else ''}")
        )
        if len(locations) > 1:
            multiple.append(tool.value)
        if not locations[0].runnable:
            unsafe_first.append(tool.value)
    status = Status.WARNING if unsafe_first else Status.INFO
    if unsafe_first:
        summary = "One or more tools are shadowed by batch launchers"
    elif multiple:
        summary = "Multiple PATH matches detected; review only if versions conflict"
    else:
        summary = "No executable shadowing detected for inspected tools"
    return CheckResult(
        "executable-shadowing",
        "Executable shadowing",
        "environment",
        status,
        summary,
        evidence=tuple(evidence),
        severity=Severity.MEDIUM if unsafe_first else Severity.INFO,
        details=(
            "Multiple installations are common and are not treated as a failure by themselves.",
            "Remote and reparse PATH locations are not traversed.",
        ),
        recommendations=("Review PATH order for the named tools; no entries were changed.",)
        if unsafe_first
        else (),
    )
