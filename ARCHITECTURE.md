# Architecture

## Decisions

Use Python 3.12+, a `src` layout, argparse, frozen dataclasses, enums and protocols.
There are no runtime dependencies. Stdlib is sufficient for this phase; a future terminal
library can be added without changing result or plugin contracts. PyInstaller provides
Windows distribution; end users of the executable will not need Python.

Dependencies point inward: CLI composes core services and plugins; diagnostics depend on
models and read-only context; reports consume sanitized models; fixes use a separate safety
service. No auto-discovery, entry-point loading, arbitrary shell plugins or untrusted plugin
execution. Plugins are trusted Python code, not a security sandbox.

## Modules and plugin contract

`models.py`: validated immutable CheckResult, status/severity and metadata.
`core/`: config, redaction, command runner, host/network/Windows adapters, registry/engine and logging.
`diagnostics/`: explicit system, developer-tool, AI-application, environment and network
modules, plus pure parsing helpers and one explicit registry.
`fixes/`: immutable plans and restricted backup operation, separate from diagnostics.
`reporting/`: a shared sanitized document, terminal/JSON/HTML views and exclusive export.
`cli.py`: argument validation and composition only.

A Check carries stable ID, name, category, explanation, network requirement and callable.
The callable receives Context (read-only host, runner, network probe and config). Inject
fakes in tests. Registration rejects duplicate IDs. Engine preserves registration order,
filters categories, returns SKIPPED for disabled checks and absent network consent, validates
returned identity, catches ordinary exceptions per check and emits a generic ERROR without
exception text. KeyboardInterrupt/SystemExit remain process-control signals.

Every result has id/name/category/status/summary/details/severity/evidence/recommendations/
fix_ids/documentation_url. Evidence is string pairs, never arbitrary process/config dumps.
Enums and IDs are validated; tuple collections make snapshots immutable. Result identity
comes from the Check definition. Report schema is versioned independently of app version.

## Read-only execution and time bounds

CommandRunner accepts enums for reviewed tools and operations, never caller-provided argv.
It supports fixed version/config/status probes for Git/GitHub CLI, Python/pip/launcher,
Node/npm/npx, PowerShell, Windows Terminal, Codex and selected version managers. It resolves
all local PATH matches from absolute entries, excludes the current directory and remote or
reparse locations, and rejects Windows batch launchers. npm/npx use `node.exe` with adjacent
reviewed CLI scripts instead of invoking `.cmd` files. Execution disables stdin/shell, uses
a minimal environment without credential/proxy values, and caps output. GitHub auth status
requires network consent and never requests token output. Timeouts kill the direct child,
drain bounded output and return a typed outcome; this is not a process-tree sandbox.

Network probes run in disposable multiprocessing workers. Separate DNS and TCP probes, plus
a staged HTTPS probe, use fixed public targets. A parent deadline covers each target; workers
are terminated/joined on timeout. TLS is verified; HTTP uses HEAD only, no redirects, proxy
credentials, cookies or arbitrary URLs. HTTPS results identify DNS/TCP/TLS/HTTP stages.
Probes are direct connectivity, not validation of the user's proxy path. Environment, system
and WinHTTP proxy inspection is offline. Adapter/default-route and localhost-listener evidence
is read through typed Win32 APIs and does not turn mere presence into a failure.

## Privacy and output boundary

Minimize collection first: don't read application secrets, Git identities, command lines or
entire environments. Redactor recursively removes sensitive-key values, known sensitive
environment values, credential assignments, bearer/basic headers, token patterns, URL
userinfo/query/fragment, email addresses, home paths and terminal control sequences. Output
paths/evidence and every renderer/log pass through this layer. Redaction cannot be disabled.
Raw subprocess text stays inside the diagnostic adapter; only parsed version escapes.
No regex can identify every arbitrary secret; don't collect unknown data in future plugins.

Logging is JSON lines, opt-in via `--log-file`, exclusively creates a local file, and records
only check ID/status, never command output or exception strings. Default diagnose writes no
logs/config/cache. JSON stdout never mixes with progress. HTML escapes every dynamic value
and embeds CSS only (no scripts, external fonts/assets or network resources).

## Fixes and filesystem boundaries

Only `backup-config` is implemented. It backs up the tool's own existing config to an
exclusive sibling file. Plan records source identity/hash, destination, risk, reversibility,
and audit location. Dry-run creates nothing. CLI shows the plan and requires typing `yes`;
noninteractive execution refuses. No `--yes` bypass. Execution requires explicit confirmation,
revalidates the exact allowed source and rejects symlinks/reparse points in all path ancestors,
changed content/identity, occupied destinations and invalid config. Backup uses exclusive
creation. Audit records intent before modification and completion afterward. If completion
logging fails, report possible successful backup and preserve it; never silently roll back.
There is no delete/registry/PATH/proxy/cache mutation primitive. A local attacker capable of
concurrent filesystem replacement is outside this user-level tool's isolation boundary;
rechecks reduce accidental races but do not constitute an OS security sandbox.

## Testing and extension rules

Unit tests cover models, config, parsing, redaction, execution and renderers. Fake adapters
cover diagnostic branches without relying on installed tools or internet. CLI integration
uses injected Context and temp directories. Security tests insert canary secrets and hostile
HTML/control characters. Process integration tests cover missing commands, output bounds
and deadlines. Windows/Linux CI catches path and spawn differences; Windows build smoke
tests cover packaged startup, offline JSON and HTML export. No live network required in CI.

Before adding an automatic fix, prove discovery, permissions, app-not-running requirements,
revalidation, exclusive backup, confirmation, audit and recovery. Prefer manual guidance
until these can be tested. Before new diagnostics, reuse the injected boundaries rather than
subprocess/network/file-writing calls inside plugins. Platform adapters may be added where
they have actual callers; avoid speculative generic abstractions.

## Reference decisions

- [Python subprocess security](https://docs.python.org/3.12/library/subprocess.html#security-considerations):
  Windows batch files can invoke a shell even with shell=False; reject them.
- [gh auth status](https://cli.github.com/manual/gh_auth_status): do not infer authentication
  from installation/version or serialize authentication output.
- [PyInstaller usage](https://pyinstaller.org/en/stable/usage.html): build Windows on Windows.

## Implementation review

Phase 2 retains the Phase 1 safety refinements and adds a typed read-only Windows boundary.
The explicit registry now contains 36 checks. Application configuration and cache checks read
only presence, timestamps, counts and aggregate sizes under known roots, with hard traversal
limits; proprietary contents are not parsed. Git configuration/repository checks expose key
presence and counts only. OS structures use Win32 APIs or documented registry locations rather
than localized command output. Unsupported, denied or ambiguous observations remain
INFO/SKIPPED instead of fabricated PASS.

### Phase 1 refinements

The first working implementation prompted four refinements: evidence key/value pairs are
sanitized together (not just as strings); parser errors do not echo raw CLI arguments;
fix definitions and immutable plans are separate from the backup implementation; and PATH
inspection/executable discovery skip UNC, mapped network drives and reparse points to
preserve offline behavior. Control-only output degrades safely instead of crashing renderers.

The shared filesystem guard lives in core/safety.py. SafetyError is defined there too; core never imports fixes.
Immutable plans live in the data-only fixes/models.py module. CLI repair lookup uses fixes/framework.py.
A future repair requiring a different plan shape should add a typed plan variant, not reuse
backup fields for unrelated operations.

Packaging uses PyInstaller onedir, not onefile: users extract a complete standalone bundle,
with no Python installation or temporary extraction on startup. CI uploads a development ZIP
only, with read-only repository permissions and pinned action commits. No release is created.
Local filesystem metadata calls still depend on OS responsiveness; arbitrary filesystem IO
cannot be guaranteed to finish by the command/network worker deadlines. Plugins and installed
executables remain trusted code, not sandboxed extensions.
