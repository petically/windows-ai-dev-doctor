"""Representative checks validate the architecture, not full product coverage."""

from ai_dev_doctor.core.commands import Command
from ai_dev_doctor.core.engine import Check, Context, Registry
from ai_dev_doctor.core.network import TARGETS, ProbeKind
from ai_dev_doctor.diagnostics.parsing import analyze_path, parse_git_version, parse_proxy
from ai_dev_doctor.models import CheckResult, Severity, Status


def system_check(ctx: Context) -> CheckResult:
    system, version, machine = ctx.host.system()
    windows = system == "Windows"
    return CheckResult(
        "windows-system",
        "Windows system",
        "system",
        Status.INFO if windows else Status.SKIPPED,
        "Windows platform detected" if windows else "Windows-specific check unavailable",
        evidence=(("platform", system), ("version", version), ("architecture", machine)),
        details=("Edition, privilege and compatibility checks are planned for Phase 2.",),
    )


def git_check(ctx: Context) -> CheckResult:
    result = ctx.runner.run(Command.GIT_VERSION, ctx.config.command_timeout)
    evidence: tuple[tuple[str, str], ...] = (("outcome", result.outcome),)
    if result.outcome == "missing":
        status, summary = Status.WARNING, "Git executable not found on absolute PATH entries"
    elif result.outcome != "completed" or result.returncode != 0 or result.truncated:
        status, summary = Status.WARNING, "Git version probe could not complete reliably"
    elif version := parse_git_version(result.stdout):
        status, summary = Status.PASS, f"Git {version} is executable"
        evidence += (("version", version), ("executable", result.executable))
    else:
        status, summary = Status.WARNING, "Git returned an unrecognized version response"
    return CheckResult(
        "git-version",
        "Git version",
        "developer-tools",
        status,
        summary,
        severity=Severity.LOW if status == Status.WARNING else Severity.INFO,
        evidence=evidence,
        recommendations=()
        if status == Status.PASS
        else ("Review the Git installation and PATH; use an official Git for Windows installer.",),
        documentation_url="https://git-scm.com/downloads/win",
    )


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
    return CheckResult(
        "path-structure",
        "PATH structure",
        "environment",
        Status.WARNING if findings else Status.PASS,
        f"{len(findings)} PATH findings"
        if findings
        else "PATH directories exist without structural issues",
        evidence=findings,
        severity=Severity.LOW if findings else Severity.INFO,
        recommendations=("Review entries manually; no PATH changes were made.",)
        if findings
        else (),
    )


def proxy_check(ctx: Context) -> CheckResult:
    env = ctx.host.environment
    evidence: list[tuple[str, str]] = []
    endpoints = set()
    malformed = False
    for key, value in env.items():
        if key.upper() not in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY") or not value:
            continue
        if key.upper() == "NO_PROXY":
            evidence.append((key, "Configured (host list omitted for privacy)"))
            continue
        endpoint = parse_proxy(value)
        if endpoint is None:
            malformed = True
            evidence.append((key, "Unrecognized proxy URL (value omitted)"))
        else:
            endpoints.add(endpoint)
            evidence.append((key, f"{endpoint.scheme}://{endpoint.host}:{endpoint.port}"))
    status = Status.WARNING if malformed else Status.INFO
    summary = (
        "Proxy environment requires review"
        if malformed
        else (
            "Proxy environment detected" if evidence else "No proxy environment variables detected"
        )
    )
    if len(endpoints) > 1:
        summary = "Multiple proxy endpoints configured; review intended routing"
    return CheckResult(
        "proxy-environment",
        "Proxy environment",
        "network",
        status,
        summary,
        evidence=tuple(evidence),
        details=(
            "Proxy presence is not a fault. System/WinHTTP/TUN and listeners are not checked here.",
        ),
        recommendations=("Compare configured endpoints with your intended proxy setup.",)
        if evidence
        else (),
    )


def _network(ctx: Context, kind: ProbeKind) -> CheckResult:
    probes = [ctx.network.probe(kind, target, ctx.config.network_timeout) for target in TARGETS]
    passed = sum(probe.ok for probe in probes)
    status = Status.PASS if passed == len(probes) else Status.WARNING if passed else Status.FAIL
    return CheckResult(
        f"network-{kind}",
        f"{kind.upper()} connectivity",
        "network",
        status,
        f"{passed}/{len(probes)} public targets succeeded",
        severity=Severity.MEDIUM if not passed else Severity.INFO,
        evidence=tuple((p.target, f"{p.stage}: {p.detail}; {p.elapsed_ms} ms") for p in probes),
        details=(
            "Direct connectivity only; configured proxies are not used. No redirects followed.",
        ),
        recommendations=()
        if status == Status.PASS
        else (
            "Review the reported failure stage; a target failure alone does not prove general outage.",
        ),
    )


def dns_check(ctx: Context) -> CheckResult:
    return _network(ctx, "dns")


def https_check(ctx: Context) -> CheckResult:
    return _network(ctx, "https")


def registry() -> Registry:
    return Registry(
        (
            Check(
                "windows-system",
                "Windows system",
                "system",
                "Read-only platform/version/architecture detection; no elevation.",
                system_check,
            ),
            Check(
                "git-version",
                "Git version",
                "developer-tools",
                "Runs only git --version with a deadline and parses the version; no credentials read.",
                git_check,
            ),
            Check(
                "path-structure",
                "PATH structure",
                "environment",
                "Checks Windows PATH for empty, relative, missing, quoted and duplicate entries; never edits PATH.",
                path_check,
            ),
            Check(
                "proxy-environment",
                "Proxy environment",
                "network",
                "Inspects proxy environment only; omits credentials and NO_PROXY host lists. Does not infer a conflict from proxy presence.",
                proxy_check,
            ),
            Check(
                "network-dns",
                "DNS connectivity",
                "network",
                "Opt-in DNS resolution of example.com and www.python.org with hard deadlines.",
                dns_check,
                True,
            ),
            Check(
                "network-https",
                "HTTPS connectivity",
                "network",
                "Opt-in direct TLS-verified HEAD probes of example.com and www.python.org; distinguishes DNS/TCP/TLS/HTTP failures.",
                https_check,
                True,
            ),
        )
    )
