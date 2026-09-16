# Product specification

## Authority and scope

The complete product brief is [Windows AI Dev Doctor — Codex 完整开发提示词.md](Windows%20AI%20Dev%20Doctor%20—%20Codex%20完整开发提示词.md).
The user's Phase 1 request narrows that brief: establish and validate the foundation,
not every diagnostic or a production release. No tag or GitHub Release in this phase.
Version during development: `0.1.0.dev0`.

## Product contract

Explain Windows 10/11 developer and AI application failures with evidence, uncertainty,
and actionable recommendations. Python 3.12+; ordinary operation needs no elevation.
No telemetry, analytics, uploads, automatic repairs, registry changes, or security changes.
Local diagnostics do not write files. Explicit report export and explicitly confirmed fixes
are separate state-changing operations. Bytecode generation is suppressed by the entry point.
External executables are trusted installed tools; their own side effects cannot be sandboxed.

Network probes are disabled by default, including when enabled in a configuration file:
only `--network` consents to outbound DNS/TCP/TLS/HEAD probes to fixed public targets.
No diagnostic data, configuration, credentials, cookies, or identifiers are sent.
Normal network metadata (IP address, DNS queries) is necessarily visible to infrastructure.
Reports are local exports, never uploads. Redaction cannot be disabled.

## Phase 1 acceptance

- CLI: diagnose/doctor, explain, fix (including dry-run), report, version, help.
- Deterministic registry, immutable validated results, per-plugin exception containment.
- Read-only injected host and bounded command/network adapters; no shell command strings.
- Strict bounded TOML configuration, safe defaults, unknown options rejected.
- Central recursive redaction and redacted structured opt-in local logging.
- Representative Windows system, Git version, PATH, proxy environment, DNS and HTTPS checks.
- Offline terminal/JSON/HTML rendering, schema version, timestamps, version and counts.
- Fix planning separated from confirmation and execution; safe configuration backup only.
- Unit/security/CLI/integration tests; lint/format/type checks; Windows and Linux CI.
- Windows executable packaging and smoke-test automation without publishing a release.
- Handoff documentation describes gaps without claiming unimplemented functionality.

## Stable interface decisions

Exit codes: 0 = no FAIL/ERROR (warnings still visible); 1 = at least one FAIL/ERROR;
2 = usage/configuration/export/fix error. JSON output on stdout is one JSON document;
diagnostic logs/errors use stderr unless a local log file is explicitly requested.
`report` defaults to JSON stdout; `.json` and `.html` output files require explicit paths
and must not overwrite existing files. Network consent applies to report runs too.

Statuses: PASS, INFO, WARNING, FAIL, SKIPPED, ERROR. Severity is independent:
info, low, medium, high. A missing optional tool is WARNING, unsupported platform or
disabled probe is SKIPPED, implementation failure is ERROR. No fabricated PASS.
Schema version `1` is separate from application version. Stable check IDs and categories
are public interfaces. Additive fields are allowed; incompatible changes require a new schema.

## Full-product coverage deferred to Phase 2

PowerShell/Terminal, Windows edition/privileges/disk/temp inspection; detailed Git config
and repository state; gh/auth, Python/pip/launchers, Node/npm/version managers; WebView2;
ChatGPT/Codex discovery; adapters/routes/system and WinHTTP proxy, localhost/listener
ownership; developer environment paths, processes, GPU information, application caches.
Best-effort findings must preserve uncertainty. Multiple installations, proxy layers and
occupied ports are not failures without corroborating evidence. No application cache
repair until trustworthy discovery, running-process guards and rollback are proven.

## Release gate (later)

All full-product acceptance criteria in the source brief, complete tests and static checks,
Windows packaged executable smoke tests, security review, current docs/changelog, clean
tree, and explicit release authorization. Phase 1 artifacts are development artifacts only.
