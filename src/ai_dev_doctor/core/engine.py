"""Explicit registry and per-check failure isolation."""

from collections.abc import Callable
from dataclasses import dataclass

from ai_dev_doctor.core.commands import Runner
from ai_dev_doctor.core.config import Config, ConfigError
from ai_dev_doctor.core.host import Host
from ai_dev_doctor.core.network import Network
from ai_dev_doctor.core.windows import NullWindowsInspector, WindowsInspector
from ai_dev_doctor.models import CheckResult, Severity, Status


@dataclass(frozen=True)
class Context:
    host: Host
    runner: Runner
    network: Network
    config: Config
    network_allowed: bool = False
    windows: WindowsInspector = NullWindowsInspector()


@dataclass(frozen=True)
class Check:
    id: str
    name: str
    category: str
    explanation: str
    run: Callable[[Context], CheckResult]
    requires_network: bool = False

    def result(self, status: Status, summary: str) -> CheckResult:
        return CheckResult(self.id, self.name, self.category, status, summary)


class Registry:
    def __init__(self, checks: tuple[Check, ...]) -> None:
        if len({check.id for check in checks}) != len(checks):
            raise ValueError("Duplicate check ID")
        for check in checks:
            check.result(Status.INFO, "Registration validation")
        self.checks = checks

    def get(self, check_id: str) -> Check:
        for check in self.checks:
            if check.id == check_id:
                return check
        raise ValueError("Unknown check ID")

    def run(self, context: Context, category: str | None = None) -> tuple[CheckResult, ...]:
        unknown = set(context.config.disabled_checks) - {c.id for c in self.checks}
        if unknown:
            raise ConfigError("Unknown disabled check ID")
        results = []
        for check in self.checks:
            if (category is not None and category != check.category) or (
                check.category not in context.config.enabled_categories
            ):
                continue
            if check.id in context.config.disabled_checks:
                result = check.result(Status.SKIPPED, "Disabled by configuration")
            elif check.requires_network and not context.network_allowed:
                result = check.result(Status.SKIPPED, "Network probe requires --network consent")
            else:
                try:
                    result = check.run(context)
                    if (result.id, result.name, result.category) != (
                        check.id,
                        check.name,
                        check.category,
                    ):
                        raise ValueError("Plugin result identity mismatch")
                except Exception:
                    # Exception messages may contain secrets or private paths.
                    result = CheckResult(
                        check.id,
                        check.name,
                        check.category,
                        Status.ERROR,
                        "Check could not complete",
                        severity=Severity.MEDIUM,
                        recommendations=("Retry and report the check ID if this persists.",),
                    )
            results.append(result)
        return tuple(results)
