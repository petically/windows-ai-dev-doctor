# Product specification

## Authority and scope

The complete product brief is [Windows AI Dev Doctor — Codex 完整开发提示词.md](Windows%20AI%20Dev%20Doctor%20—%20Codex%20完整开发提示词.md).
Phase 1 established the architecture and safety foundation. Phase 2 implements the reasonable
diagnostic depth of that brief without authorizing a production release. No tag or GitHub
Release may be created without explicit authorization. Development version: `0.1.0.dev0`.

## Product contract

Explain Windows 10/11 developer and AI application failures with evidence, uncertainty,
and actionable recommendations. Python 3.12+; ordinary operation needs no elevation.
No telemetry, analytics, uploads, automatic repairs, registry changes, or security changes.
Local diagnostics do not write files. Explicit report/log export and the explicitly confirmed
configuration backup are separate state-changing operations. Bytecode generation is suppressed
by the entry point. External executables are trusted installed tools; their own side effects
cannot be sandboxed.

Network probes are disabled by default, including when enabled in a configuration file:
only `--network` consents to outbound DNS/TCP/TLS/HEAD probes to fixed public targets and
the GitHub CLI authentication status probe. No diagnostic data, configuration, credentials,
cookies or identifiers are sent by this tool. Normal network metadata is necessarily visible
to infrastructure. Reports are local exports, never uploads. Redaction cannot be disabled.

## Implemented acceptance

- CLI: diagnose/doctor, explain, fix (including dry-run), report, version and help.
- Deterministic 36-check registry, immutable validated results and per-plugin containment.
- Read-only injected host/Windows boundaries and bounded command/network adapters.
- Strict bounded TOML configuration, safe defaults and rejection of unknown options.
- Central recursive redaction and redacted structured opt-in local logging.
- Windows system/privilege/disk/directory/WebView2/GPU/process and application discovery.
- Git/GitHub CLI, Python/pip/launcher, Node/npm/npx, PowerShell/Terminal, Codex and manager checks.
- PATH/environment/shadowing, privacy-preserving Git config/repository summaries.
- Environment/system/WinHTTP proxy, adapters/routes/listeners and proxy-layer correlation.
- Explicitly consented DNS, TCP and HTTPS connectivity stages with fixed targets.
- Best-effort ChatGPT/Codex metadata without proprietary content parsing.
- Offline terminal/JSON/HTML rendering, schema version, timestamps, version and counts.
- Safe planning/confirmation/execution framework; config backup is the only automatic fix.
- Unit/security/CLI/integration tests, lint/format/type checks and Windows/Linux CI.
- Windows onedir executable packaging and smoke-test automation without a release.

## Stable interface decisions

Exit codes: 0 = no FAIL/ERROR (warnings still visible); 1 = at least one FAIL/ERROR;
2 = usage/configuration/export/fix error. JSON output on stdout is one JSON document;
diagnostic logs/errors use stderr unless a local log file is explicitly requested.
`report` defaults to JSON stdout; `.json` and `.html` output files require explicit paths
and never overwrite existing files. Network consent applies to report runs too.

Statuses: PASS, INFO, WARNING, FAIL, SKIPPED, ERROR. Severity is independent:
info, low, medium, high. A missing optional tool is WARNING, unsupported platform or
disabled probe is SKIPPED, implementation failure is ERROR. No fabricated PASS.
Schema version `1` is separate from application version. Stable check IDs and categories
are public interfaces. Additive fields are allowed; incompatible changes require a new schema.

## Qualified limitations

Best-effort application and registry discovery can become incomplete as Store/package layouts
change. Multiple installations, proxy layers and occupied ports are not failures without
corroborating evidence. Direct connectivity does not validate configured proxies. Cache
inspection is bounded metadata only; no application cache repair exists because trustworthy
ownership, process guards and rollback are not proven. Installed tools/plugins are trusted,
and direct-child timeouts are not a process-tree sandbox.

## Release gate (later)

Audit all original acceptance criteria; expand threat-model/redaction review; review false
positives and Win32 structure handling; verify the unsigned standalone distribution on clean
supported Windows 10/11 machines; decide on signing/installer requirements; validate install
instructions; obtain explicit release authorization.
