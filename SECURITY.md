# Security and privacy

This is a pre-release diagnostic tool, not a production-certified system repair utility.
Only the current main branch receives fixes during pre-release development.

## Reporting

Use GitHub's private vulnerability reporting if enabled on this repository. Otherwise
open an issue containing only a request for a private reporting channel, without exploit
details or secrets. Do not post credentials or unredacted diagnostic reports publicly.

## Boundaries

Trusted built-in Python plugins are not sandboxed. Installed tool executables must be
trusted. The command allowlist contains fixed version/config/status probes for explicitly
supported developer tools. It resolves absolute executable paths, rejects batch launchers,
does not use a shell or stdin, and omits API keys, auth tokens and proxy credentials from
the child environment. GitHub authentication status additionally requires `--network` and
never requests token output. Time and output bounds do not make hostile binaries safe.
Windows commands start inside a private kill-on-close Job Object before their initial thread
runs. Descendants cannot request breakaway through this job; setup failures refuse execution.
Only the three standard IO handles are inherited. Completion, timeout and cancellation close
the job; unrelated processes are never selected by name or PID for termination. POSIX uses
an owned process group; malicious children that escape that group remain outside its guarantee.
Neither adapter restricts installed-tool file access or acts as an OS security sandbox.

The Windows adapter uses read-only Win32 APIs and documented registry locations. It collects
names or aggregate metadata needed for findings, not command lines, Git identities, file
names, configuration/cache contents or raw environment dumps. Registry/API layout changes
or access controls can make a check return INFO/SKIPPED; uncertainty is not converted to PASS.

Network workers use fixed public targets, verified TLS and bounded lifetimes. Normal network
metadata is visible when `--network` is explicitly used. Direct probes do not test a configured
proxy route. Reports are local exports, never uploads. There is no telemetry. Redaction is
mandatory but cannot recognize every unknown secret: minimize collection and review exports
before sharing.

Fixes reject symlink/reparse paths, changed inputs and existing destinations. They require
interactive confirmation and an intent audit before mutation. The only implemented fix backs
up this tool's own valid configuration and preserves the original. A crash/disk failure can
leave a partial backup or intent-only audit; retain the original, inspect the audit, and retry
with a new plan. Concurrent malicious filesystem replacement by another process running as
the same user is outside this tool's isolation boundary. There is no cache deletion, automatic
elevation, driver/security change, or PATH/proxy/registry mutation.

Do not run this development tool as Administrator. Do not add arbitrary command execution,
recursive deletion or automatic registry/PATH/proxy edits to the diagnostic context.


The v0.1.0 distribution strategy is an unsigned portable x64 bundle with a published SHA-256
checksum. SmartScreen/reputation warnings are possible. A checksum verifies artifact integrity,
not publisher identity; obtain artifacts from this repository's release page. No installer,
certificate fabrication or security-control bypass is part of the release process.

The source credential/path scan recognizes specific patterns and build-machine paths. The
privacy canary suite exercises every renderer and logging, but cannot recognize every opaque
secret. Source distribution contents are allowlisted so unrelated local Markdown is not shipped.
