# Changelog

## 0.1.0 - 2026-09-17

Initial portable Windows x64 release with 36 offline-first diagnostics.

### Phase 3 release hardening

- Contain Windows probe descendants atomically in kill-on-close Job Objects, including
  cancellation and successful-parent exit; no uncontained fallback or unrelated process kills.
- Validate Win32 adapter/TCP buffers, preserve process-enumeration uncertainty and restrict
  localhost evidence to loopback/wildcard listeners.
- Reduce optional-tool, Git identity, Codex configuration, inactive-proxy and IPv6 false positives.
- Harden redaction for escaped/multiline credentials, folded headers, generic URI credentials,
  connection strings, private keys and personal paths across reports and logs.
- Prevent optional Git index updates, fsmonitor hooks and submodule traversal during inspection.
- Fix Linux strict type checks, enforce UTF-8 CLI output and add Windows 2022/2025 CI.
- Add PE version metadata, explicit source-package contents, source privacy scan and relocated
  Unicode/spaced-path portable smoke tests with no-overwrite checks.
- Select unsigned portable x64 packaging; defer installer/signing and explicitly track client
  Windows 10/11 clean-machine validation as unverified.

### Phase 2 coverage

- Expanded the deterministic registry from 6 to 36 diagnostics across system, developer
  tools, AI applications, environment and network categories.
- Added a read-only Windows adapter for structured OS, privilege, disk, directory, WebView2,
  proxy, adapter/route, listener/process, GPU and application metadata.
- Added reviewed Git/GitHub CLI, Python, pip, Node.js, npm/npx, PowerShell, Terminal, Codex
  and version-manager discovery/version checks.
- Added privacy-preserving Git configuration/repository summaries, executable shadowing,
  developer environment validation and bounded ChatGPT/Codex cache metadata.
- Added system/WinHTTP proxy correlation, adapter/default-route context, localhost listener
  evidence and explicitly consented DNS, TCP and HTTPS network stages.
- Expanded fake-adapter, parser, privacy, command-safety and packaged smoke coverage.
- Updated documentation and packaging smoke expectations for the complete Phase 2 registry.
- The initial portable release remains unsigned; Windows reputation warnings may occur.

### Phase 1 foundation

- Established product scope, architecture contracts, roadmap and engineering-agent handoff.
- Added standard-library CLI, immutable result model, explicit registry and check isolation.
- Added strict configuration, command allowlist, bounded network workers and mandatory redaction.
- Added Windows metadata, Git version, PATH, proxy environment and optional DNS/HTTPS checks.
- Added terminal/JSON/HTML reports and explicit local structured logging.
- Added dry-run and confirmed, audited backup of the tool's own configuration.
- Added unit, integration, security and CLI tests, static checks and Windows/Linux CI.
- Added Windows standalone development-bundle packaging and smoke tests.
- Phase 1 was an unreleased foundation milestone.
