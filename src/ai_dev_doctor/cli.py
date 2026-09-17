"""CLI composition; diagnostics, renderers and repairs remain independent."""

import argparse
import io
import os
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Never

from ai_dev_doctor import __version__
from ai_dev_doctor.core.commands import CommandRunner
from ai_dev_doctor.core.config import CATEGORIES, ConfigError, config_path, load_config
from ai_dev_doctor.core.engine import Context
from ai_dev_doctor.core.host import LocalHost
from ai_dev_doctor.core.logging import write_event
from ai_dev_doctor.core.network import NetworkProbe
from ai_dev_doctor.core.redaction import Redactor
from ai_dev_doctor.core.windows import LocalWindowsInspector
from ai_dev_doctor.diagnostics.builtin import registry
from ai_dev_doctor.fixes.backup import SafetyError
from ai_dev_doctor.fixes.framework import DEFINITIONS, get_fix
from ai_dev_doctor.models import exit_code
from ai_dev_doctor.reporting import export, render_html, render_json, render_terminal


class SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        # Do not echo arbitrary secret-bearing arguments in parser errors.
        self.print_usage(sys.stderr)
        self.exit(2, "Error: invalid arguments; use --help for supported options\n")


def parser() -> argparse.ArgumentParser:
    app = SafeParser(prog="ai-dev-doctor", description="Safe, offline-first Windows diagnostics")
    commands = app.add_subparsers(dest="command", required=True)
    for name in ("diagnose", "doctor", "report"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--category", choices=CATEGORIES)
        cmd.add_argument(
            "--network", action="store_true", help="Consent to direct public DNS/HTTPS probes"
        )
        cmd.add_argument("--verbose", action="store_true")
        cmd.add_argument("--json", action="store_true", help="JSON on stdout")
        cmd.add_argument("--config", type=Path)
        cmd.add_argument(
            "--log-file", type=Path, help="Explicitly create a local redacted event log"
        )
        if name == "report":
            cmd.add_argument(
                "--output", type=Path, help="Create a new .json or .html file (no overwrite)"
            )
    explain = commands.add_parser("explain")
    explain.add_argument("check_id")
    fix = commands.add_parser("fix")
    fix.add_argument("fix_id", choices=tuple(d.id for d in DEFINITIONS))
    fix.add_argument("--dry-run", action="store_true")
    commands.add_parser("version")
    commands.add_parser("help")
    return app


def _fix(fix_id: str, dry_run: bool, redactor: Redactor) -> int:
    operation = get_fix(fix_id, config_path())
    plan = operation.plan()
    for label, value in (
        ("Action", plan.action),
        ("Reason", plan.reason),
        ("Risk", plan.risk),
        ("Reversible", plan.reversible),
        ("Original", str(plan.source)),
        ("Backup", str(plan.backup)),
        ("Audit", str(plan.audit)),
    ):
        print(redactor.text(f"{label}: {value}"))
    if dry_run:
        print("Dry run: no files changed. A later invocation creates a new unique plan.")
        return 0
    if not sys.stdin.isatty():
        raise SafetyError("Interactive confirmation is required; use --dry-run to preview")
    confirmed = input("Proceed? Type yes [default: NO]: ").strip().lower() == "yes"
    if not confirmed:
        print("Cancelled; no files changed.")
        return 0
    operation.execute(plan, confirmed=True, redactor=redactor)
    print("Backup created; original configuration unchanged. Audit stored beside the backup.")
    return 0


def main(argv: Sequence[str] | None = None, *, context: Context | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    app = parser()
    # argparse never echoes arbitrary secret-bearing argument values to stderr.
    try:
        args = app.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    redactor = Redactor.from_environment(os.environ, str(Path.home()))
    try:
        if args.command == "version":
            print(__version__)
            return 0
        if args.command == "help":
            app.print_help()
            return 0
        checks = registry()
        if args.command == "explain":
            check = checks.get(args.check_id)
            print(f"{check.id}: {check.name}\n{check.explanation}")
            return 0
        if args.command == "fix":
            return _fix(args.fix_id, args.dry_run, redactor)
        cfg = load_config(args.config or config_path(), required=args.config is not None)
        if context is None:
            environment = dict(os.environ)
            context = Context(
                LocalHost(),
                CommandRunner(environment),
                NetworkProbe(),
                cfg,
                args.network,
                LocalWindowsInspector(environment),
            )
        else:
            context = replace(context, config=cfg, network_allowed=args.network)
        output = getattr(args, "output", None)
        if output is not None and args.json:
            raise ValueError("--json and --output cannot be combined")
        if output is not None and output.suffix.lower() not in (".json", ".html"):
            raise ValueError("Report output must end in .json or .html")
        results = checks.run(context, args.category)
        if args.log_file:
            with args.log_file.open("x", encoding="utf-8") as log:
                for result in results:
                    write_event(
                        log,
                        redactor,
                        "check-completed",
                        check_id=result.id,
                        status=result.status.value,
                    )
        if output is not None:
            content = (
                render_html(results, redactor)
                if output.suffix.lower() == ".html"
                else render_json(results, redactor)
            )
            export(output, content)
            print(redactor.text(f"Report created: {output}"))
        elif args.json or args.command == "report":
            print(render_json(results, redactor), end="")
        else:
            print(
                render_terminal(
                    results,
                    redactor,
                    verbose=args.verbose or cfg.verbose,
                    color=sys.stdout.isatty() and "NO_COLOR" not in os.environ,
                ),
                end="",
            )
        return exit_code(results)
    except (ConfigError, SafetyError, ValueError) as exc:
        print("Error: " + redactor.text(str(exc)), file=sys.stderr)
        return 2
    except OSError:
        print(
            "Error: local file or operation unavailable; check permissions and existing destinations",
            file=sys.stderr,
        )
        return 2
    except (KeyboardInterrupt, EOFError):
        print("Cancelled", file=sys.stderr)
        return 130
