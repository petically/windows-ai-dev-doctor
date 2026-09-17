"""Developer-tool diagnostics using reviewed, bounded commands only."""

from ai_dev_doctor.core.commands import Command, Tool
from ai_dev_doctor.core.engine import Context
from ai_dev_doctor.diagnostics.parsing import (
    parse_git_status,
    parse_git_version,
    parse_version_token,
)
from ai_dev_doctor.models import CheckResult, Severity, Status


def _version_result(
    ctx: Context,
    *,
    check_id: str,
    name: str,
    command: Command,
    tool: Tool,
    documentation_url: str,
    optional: bool = False,
) -> CheckResult:
    result = ctx.runner.run(command, ctx.config.command_timeout)
    locations = ctx.runner.locations(tool)
    evidence: list[tuple[str, str]] = [("outcome", result.outcome)]
    if result.executable:
        evidence.append(("probe-executable", result.executable))
    if locations:
        evidence.append(("path-matches", str(len(locations))))
    version = (
        parse_version_token(result.stdout)
        if result.outcome == "completed" and result.returncode == 0 and not result.truncated
        else None
    )
    if version:
        status, summary = Status.PASS, f"{name} {version} is executable"
        evidence.append(("version", version))
    elif result.outcome == "missing":
        status = Status.INFO
        summary = f"{name} not found on inspected local PATH entries"
    elif result.outcome == "blocked":
        status = Status.INFO
        summary = f"{name} uses a batch launcher that this probe does not execute"
    else:
        status = Status.WARNING
        summary = f"{name} version probe could not complete reliably"
    details = []
    if len(locations) > 1:
        details.append(
            f"{len(locations)} PATH matches were found; multiple installations are not automatically a fault."
        )
    if optional and status != Status.PASS:
        details.append("This tool is optional unless your workflow depends on it.")
    return CheckResult(
        check_id,
        name,
        "developer-tools",
        status,
        summary,
        severity=Severity.LOW if status == Status.WARNING else Severity.INFO,
        evidence=tuple(evidence),
        details=tuple(details),
        recommendations=()
        if status != Status.WARNING
        else (f"Review the {name} installation and PATH ordering.",),
        documentation_url=documentation_url,
    )


def git_check(ctx: Context) -> CheckResult:
    result = ctx.runner.run(Command.GIT_VERSION, ctx.config.command_timeout)
    locations = ctx.runner.locations(Tool.GIT)
    evidence: list[tuple[str, str]] = [("outcome", result.outcome)]
    if result.executable:
        evidence.append(("probe-executable", result.executable))
    if locations:
        evidence.append(("path-matches", str(len(locations))))
    if result.outcome == "missing":
        status, summary = Status.INFO, "Git executable not found on inspected local PATH entries"
    elif result.outcome != "completed" or result.returncode != 0 or result.truncated:
        status, summary = Status.WARNING, "Git version probe could not complete reliably"
    elif version := parse_git_version(result.stdout):
        status, summary = Status.PASS, f"Git {version} is executable"
        evidence.append(("version", version))
    else:
        status, summary = Status.WARNING, "Git returned an unrecognized version response"
    return CheckResult(
        "git-version",
        "Git version",
        "developer-tools",
        status,
        summary,
        severity=Severity.LOW if status == Status.WARNING else Severity.INFO,
        evidence=tuple(evidence),
        details=(f"{len(locations)} PATH matches found; confirm the first is intended.",)
        if len(locations) > 1
        else (),
        recommendations=()
        if status != Status.WARNING
        else ("Review the Git installation and PATH; use an official Git for Windows installer.",),
        documentation_url="https://git-scm.com/downloads/win",
    )


def git_config_check(ctx: Context) -> CheckResult:
    if not ctx.runner.locations(Tool.GIT):
        return CheckResult(
            "git-config",
            "Git global configuration",
            "developer-tools",
            Status.SKIPPED,
            "Git is not available",
        )
    identity = ctx.runner.run(Command.GIT_IDENTITY_KEYS, ctx.config.command_timeout)
    branch = ctx.runner.run(Command.GIT_DEFAULT_BRANCH, ctx.config.command_timeout)
    helper = ctx.runner.run(Command.GIT_CREDENTIAL_HELPER_KEYS, ctx.config.command_timeout)
    keys = {line.strip() for line in identity.stdout.splitlines()}
    has_name = "user.name" in keys
    has_email = "user.email" in keys
    missing = [
        label
        for label, present in (("user.name", has_name), ("user.email", has_email))
        if not present
    ]
    reliable = all(
        result.outcome == "completed" and result.returncode in (0, 1) and not result.truncated
        for result in (identity, branch, helper)
    )
    if not reliable:
        status, summary = Status.WARNING, "Git global configuration could not be inspected reliably"
    elif missing:
        status, summary = (
            Status.INFO,
            "Global Git identity keys are not both present; local identity may be configured",
        )
    else:
        status, summary = (
            Status.INFO,
            "Global Git identity keys are present; values are not validated",
        )
    evidence = (
        ("user.name", "configured" if has_name else "not configured" if reliable else "unknown"),
        ("user.email", "configured" if has_email else "not configured" if reliable else "unknown"),
        (
            "default-branch",
            "configured" if branch.returncode == 0 else "not configured" if reliable else "unknown",
        ),
        (
            "git-helper",
            "configured" if helper.returncode == 0 else "not configured" if reliable else "unknown",
        ),
    )
    return CheckResult(
        "git-config",
        "Git global configuration",
        "developer-tools",
        status,
        summary,
        evidence=evidence,
        severity=Severity.LOW if not reliable else Severity.INFO,
        details=("Identity values and credential-helper contents are deliberately not collected.",),
        recommendations=(
            "If committing fails, review effective local and global Git identity configuration.",
        )
        if missing and reliable
        else (),
    )


def git_repository_check(ctx: Context) -> CheckResult:
    if not ctx.runner.locations(Tool.GIT):
        return CheckResult(
            "git-repository",
            "Git repository state",
            "developer-tools",
            Status.SKIPPED,
            "Git is not available",
        )
    result = ctx.runner.run(Command.GIT_REPOSITORY, ctx.config.command_timeout)
    if result.outcome != "completed" or result.truncated:
        return CheckResult(
            "git-repository",
            "Git repository state",
            "developer-tools",
            Status.WARNING,
            "Repository state probe did not complete reliably",
            severity=Severity.LOW,
        )
    if result.returncode != 0:
        return CheckResult(
            "git-repository",
            "Git repository state",
            "developer-tools",
            Status.SKIPPED,
            "Current directory is not an inspectable Git work tree",
        )
    state = parse_git_status(result.stdout)
    if state is None:
        return CheckResult(
            "git-repository",
            "Git repository state",
            "developer-tools",
            Status.WARNING,
            "Git returned an unrecognized repository status",
            severity=Severity.LOW,
        )
    return CheckResult(
        "git-repository",
        "Git repository state",
        "developer-tools",
        Status.WARNING if state.conflicts else Status.INFO,
        f"{state.tracked_changes} tracked change{'s' if state.tracked_changes != 1 else ''}; "
        f"{state.untracked} untracked; "
        f"{state.conflicts} conflict{'s' if state.conflicts != 1 else ''}",
        evidence=(
            ("tracked-changes", str(state.tracked_changes)),
            ("untracked", str(state.untracked)),
            ("conflicts", str(state.conflicts)),
            ("branch-metadata", "available" if state.branch_known else "unavailable"),
        ),
        severity=Severity.HIGH if state.conflicts else Severity.INFO,
        details=("Branch names, file names, remotes and commit contents are not reported.",),
        recommendations=("Resolve repository conflicts before continuing.",)
        if state.conflicts
        else (),
    )


def github_cli_check(ctx: Context) -> CheckResult:
    return _version_result(
        ctx,
        check_id="github-cli",
        name="GitHub CLI",
        command=Command.GH_VERSION,
        tool=Tool.GH,
        documentation_url="https://cli.github.com/",
        optional=True,
    )


def github_auth_check(ctx: Context) -> CheckResult:
    if not ctx.runner.locations(Tool.GH):
        return CheckResult(
            "github-auth",
            "GitHub CLI authentication",
            "developer-tools",
            Status.SKIPPED,
            "GitHub CLI is not installed",
        )
    result = ctx.runner.run(Command.GH_AUTH_STATUS, ctx.config.command_timeout)
    if result.outcome == "completed" and result.returncode == 0 and not result.truncated:
        status, summary = Status.PASS, "GitHub CLI stored active account authenticated successfully"
    elif result.outcome == "completed":
        status, summary = (
            Status.WARNING,
            "GitHub CLI stored-account probe did not succeed; connectivity or authentication may be responsible",
        )
    else:
        status, summary = Status.WARNING, "GitHub CLI authentication check could not complete"
    return CheckResult(
        "github-auth",
        "GitHub CLI authentication",
        "developer-tools",
        status,
        summary,
        severity=Severity.MEDIUM if status == Status.WARNING else Severity.INFO,
        evidence=(("outcome", result.outcome),),
        details=("Account names, scopes, tokens and command output are not retained.",),
        recommendations=(
            "Check connectivity and run gh auth status yourself; environment-token authentication was not tested.",
        )
        if status == Status.WARNING
        else (),
        documentation_url="https://cli.github.com/manual/gh_auth_status",
    )


def python_check(ctx: Context) -> CheckResult:
    result = _version_result(
        ctx,
        check_id="python-runtime",
        name="Python",
        command=Command.PYTHON_VERSION,
        tool=Tool.PYTHON,
        documentation_url="https://www.python.org/downloads/windows/",
    )
    if "VIRTUAL_ENV" in ctx.host.environment:
        return CheckResult(
            result.id,
            result.name,
            result.category,
            result.status,
            result.summary,
            details=(*result.details, "A virtual environment is active."),
            severity=result.severity,
            evidence=(*result.evidence, ("virtual-environment", "active")),
            recommendations=result.recommendations,
            documentation_url=result.documentation_url,
        )
    return result


def py_launcher_check(ctx: Context) -> CheckResult:
    return _version_result(
        ctx,
        check_id="python-launcher",
        name="Python launcher",
        command=Command.PY_LAUNCHER_VERSION,
        tool=Tool.PY_LAUNCHER,
        documentation_url="https://docs.python.org/3/using/windows.html",
        optional=True,
    )


def pip_check(ctx: Context) -> CheckResult:
    return _version_result(
        ctx,
        check_id="pip",
        name="pip",
        command=Command.PIP_VERSION,
        tool=Tool.PIP,
        documentation_url="https://pip.pypa.io/",
        optional=True,
    )


def node_check(ctx: Context) -> CheckResult:
    return _version_result(
        ctx,
        check_id="node-runtime",
        name="Node.js",
        command=Command.NODE_VERSION,
        tool=Tool.NODE,
        documentation_url="https://nodejs.org/",
    )


def npm_check(ctx: Context) -> CheckResult:
    return _version_result(
        ctx,
        check_id="npm",
        name="npm",
        command=Command.NPM_VERSION,
        tool=Tool.NPM,
        documentation_url="https://docs.npmjs.com/",
        optional=True,
    )


def npx_check(ctx: Context) -> CheckResult:
    return _version_result(
        ctx,
        check_id="npx",
        name="npx",
        command=Command.NPX_VERSION,
        tool=Tool.NPX,
        documentation_url="https://docs.npmjs.com/cli/commands/npx",
        optional=True,
    )


def version_manager_check(ctx: Context) -> CheckResult:
    evidence: list[tuple[str, str]] = []
    for variable, label in (
        ("NVM_HOME", "nvm-windows"),
        ("FNM_DIR", "fnm"),
        ("PYENV_ROOT", "pyenv"),
    ):
        if ctx.host.environment.get(variable):
            evidence.append((label, f"{variable} configured"))
    for tool in (Tool.NVM, Tool.FNM):
        locations = ctx.runner.locations(tool)
        if locations:
            suffix = "es" if len(locations) != 1 else ""
            evidence.append((tool.value, f"{len(locations)} PATH match{suffix}"))
    return CheckResult(
        "version-managers",
        "Version managers",
        "developer-tools",
        Status.INFO,
        "Version manager indicators detected"
        if evidence
        else "No supported version manager indicators detected",
        evidence=tuple(evidence),
        details=("Presence is informational; version managers are not treated as conflicts.",),
    )
