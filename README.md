English | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md)

# Windows AI Dev Doctor

Explain Windows developer-tool problems with evidence, conservative findings, and explicit safe actions.

**v0.1.0 · portable Windows x64 CLI**

This project helps answer “why does my AI/developer tool not work on Windows?” It never
claims that proxy presence, multiple installations, or an occupied port alone proves a fault.

## Available now

The explicit registry contains 36 checks:

| Category | Coverage |
| --- | --- |
| System (9) | Windows edition/build, PowerShell, Terminal, privilege, disk, important directories, WebView2, GPU, relevant processes |
| Developer tools (12) | Git version/config/repository, GitHub CLI/auth, Python/launcher/pip, Node/npm/npx, version managers |
| AI applications (3) | ChatGPT Desktop discovery, Codex CLI version, Codex configuration/cache metadata |
| Environment (3) | PATH structure, selected developer paths, executable shadowing |
| Network (9) | Environment/system/WinHTTP proxy, adapters/routes, listeners, proxy-layer correlation, DNS/TCP/HTTPS |

CLI, per-check failure isolation, strict TOML config, mandatory redaction, opt-in local
JSON/HTML reports and logs, and a confirmed configuration-backup framework are implemented.
There are no runtime Python package dependencies. Application discovery is best-effort:
proprietary state is not parsed, and uncertain or unsupported observations are INFO/SKIPPED.

Example output (illustrative, not a measurement of your machine):

```text
Windows AI Dev Doctor 0.1.0

System
  [PASS] Windows system: Windows 11 platform detected
Developer Tools
  [PASS] Git version: Git 2.49.0.windows.1 is executable
AI Applications
  [INFO] ChatGPT Desktop: ChatGPT indicators were found
Environment
  [WARNING] PATH structure: 2 PATH findings
Network
  [INFO] Proxy environment: Proxy environment detected
  [SKIPPED] DNS connectivity: Network probe requires --network consent
  [SKIPPED] TCP connectivity: Network probe requires --network consent
  [SKIPPED] HTTPS connectivity: Network probe requires --network consent
```

## Installation

For development, use Python 3.12+ on Windows 10/11:

```powershell
git clone https://github.com/petically/windows-ai-dev-doctor.git
cd windows-ai-dev-doctor
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\ai-dev-doctor.exe help
```

Download the **portable Windows x64 ZIP** and `SHA256SUMS.txt` from the
[v0.1.0 release](https://github.com/petically/windows-ai-dev-doctor/releases/tag/v0.1.0).
Compare its hash with `Get-FileHash .\ai-dev-doctor-0.1.0-windows-x64.zip -Algorithm SHA256`.
The archive contains the executable and its bundled runtime. Extract the entire folder and run `ai-dev-doctor.exe`; Python is not
required. Keep the `_internal` folder beside the executable. The portable bundle is unsigned; Windows SmartScreen/reputation warnings may appear.
There is no installer. Verify the download source and published checksum; do not disable
Windows security controls. [CI artifacts](https://github.com/petically/windows-ai-dev-doctor/actions)
may require a GitHub login to download.

An onedir package is deliberate: fast startup and no onefile runtime extraction writes.
Do not copy only the executable out of its bundle.

## Usage

After activating your environment (or from the extracted executable directory):

```powershell
ai-dev-doctor diagnose
ai-dev-doctor doctor
ai-dev-doctor diagnose --verbose
ai-dev-doctor diagnose --json
ai-dev-doctor diagnose --category ai-applications
ai-dev-doctor diagnose --category network
ai-dev-doctor diagnose --network
ai-dev-doctor explain git-repository
ai-dev-doctor report --output doctor-report.json
ai-dev-doctor report --output doctor-report.html
ai-dev-doctor diagnose --log-file local-events.jsonl
ai-dev-doctor fix --dry-run backup-config
ai-dev-doctor fix backup-config
ai-dev-doctor version
```

Network probes require `--network` on each invocation, including reports. They query
`example.com` and `www.python.org` directly, without proxy credentials or redirects.
A direct probe does not validate the configured proxy route. Unknown arguments/config options
are errors. Exit codes: **0** no FAIL/ERROR, **1** diagnostic FAIL/ERROR, **2** invocation,
configuration, export or fix failure; cancellation returns **130**.

Terminal output has ASCII status labels, optional TTY colors, and respects `NO_COLOR`.
JSON stdout is a single document; errors go to stderr.

## Configuration

Optional default: `%USERPROFILE%\.ai-dev-doctor\config.toml`. Nothing is created automatically.
A custom config can be passed with `diagnose --config path.toml` (also supported by report).
Example:

```toml
network_timeout = 4.0
command_timeout = 4.0
enabled_categories = ["system", "developer-tools", "ai-applications", "environment", "network"]
disabled_checks = []
verbose = false
```

Timeouts must be 0.1–30 seconds, per command or per network target. Config is capped at 64 KiB.
Network consent and redaction cannot be disabled/enabled through config. Unknown check IDs
and options are rejected rather than silently ignored.

## Safety and privacy

- Diagnostics inspect state without editing configuration or writing logs by default.
- No telemetry, analytics or uploads. Reports and logs stay local.
- Outbound probes require explicit consent; normal DNS/IP metadata is visible on the network.
- Secrets are removed at output boundaries. Collection is minimized; no auth/config dumps.
- Git configuration checks report only selected key presence; repository checks report counts,
  never identities, branches, remotes or file names. Git status disables optional index
  updates, fsmonitor hooks and submodule traversal.
- ChatGPT/Codex cache inspection is bounded metadata only: directory/file counts and aggregate
  sizes. It never reads cache or configuration contents and offers no cache deletion.
- Remote/reparse PATH locations are not traversed, preventing accidental share access.
- Commands use a reviewed allowlist, explicit executable paths, bounded output/deadlines,
  no shell or stdin, and a minimal environment. Windows child trees are assigned atomically
  to an owned Job Object and cleaned on completion, timeout or cancellation. Installed
  executables must still be trusted.
- Report/log files require explicit paths and never overwrite existing files.
- The only fix backs up **this tool's own existing valid configuration**. It previews the
  source, backup and audit file, defaults to NO, requires interactive `yes`, rechecks input,
  rejects reparse/symlink paths and records intent/outcome. Dry-run creates nothing.
- The original configuration is retained. To restore after later manual edits, inspect the
  backup and copy its contents back manually; the tool does not silently overwrite it.

Redaction is defense in depth, not proof that arbitrary text contains no secrets. Review
exports before sharing. See [SECURITY.md](SECURITY.md) and [ARCHITECTURE.md](ARCHITECTURE.md).

## Reports

JSON schema version `1` includes UTC timestamp, app version, system metadata, status counts
and structured results. HTML is self-contained, escaped, responsive and usable offline.
No scripts, external assets or automatic browser launch. Existing destinations are refused.

## Development and validation

The Windows adapter uses structured Win32 APIs and documented registry locations where
available. On non-Windows hosts, platform-specific checks return SKIPPED, which keeps the
test and report pipeline portable without pretending Windows state was measured.

Known limitations:

- GitHub authentication and fixed-target connectivity require `--network`; direct probes do
  not prove that a configured proxy works.
- Installed executables and built-in plugins are trusted; command deadlines are not a sandbox.
- Discovery of Store/package-managed applications can be incomplete across future layouts.
- The bundle is unsigned. Local Windows 11 validation does not establish clean Windows 10/11,
  Store-layout, ARM64 or enterprise-policy compatibility; see [validation evidence](RELEASE_READINESS.md).
- Listener correlation and reference-route evidence are IPv4-only. IPv6/localhost-name
  proxies and automatic proxy discovery remain unverified.
- Git identity checks inspect global key presence only; local identities and values are not
  validated. Authentication probes test stored GitHub accounts, excluding environment tokens.

```powershell
python -m pip install -e ".[dev,build]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src tests
python scripts/scan_source.py
python -m build
python -m PyInstaller --clean --noconfirm ai-dev-doctor.spec
python scripts/smoke_package.py dist/ai-dev-doctor/ai-dev-doctor.exe
```

Use the virtual environment's Python. Tests use fake system/network state and controlled
child processes. Windows Server 2022/2025 and Linux CI test Python 3.12/3.13; Windows also builds and
smoke-tests the standalone bundle. Local filesystem probes rely on OS responsiveness;
this is not a sandbox for malicious plugins, executables or concurrent local attackers.

## Contributing and license

Start with [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md), the
[specification](SPEC.md), and the [architecture](ARCHITECTURE.md).
Community expectations are in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
MIT licensed; see [LICENSE](LICENSE).

Implemented diagnostics and configuration backup are listed above. Application discovery,
GPU registry evidence and proxy/tunnel classification are **best-effort**. Cache repair,
proprietary application-state diagnosis, signing and an installer are **planned**, not
implemented. Missing optional software is informational; inaccessible state cannot prove a
fault. Command stdout/stderr is not a report attachment. Redirected CLI output is UTF-8.
