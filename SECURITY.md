# Security and privacy

This is a development foundation, not a production-certified system repair tool.
Only the current main branch receives fixes during pre-release development.

## Reporting

Use GitHub's private vulnerability reporting if enabled on this repository. Otherwise
open an issue containing only a request for a private reporting channel, without exploit
details or secrets. Do not post credentials or unredacted diagnostic reports publicly.

## Boundaries

Trusted built-in Python plugins are not sandboxed. Installed tool executables must be
trusted. The command allowlist currently contains only Git's version probe; it rejects
batch launchers and does not inherit API keys or proxy credentials. Time and output bounds
do not make hostile binaries safe. Only the direct command child is killed on timeout;
new commands that create descendants need a reviewed process-tree containment strategy.

Network workers use fixed public targets, verified TLS and bounded lifetimes. Normal
network metadata is visible when --network is explicitly used. Reports are local exports,
never uploads. There is no telemetry. Redaction is mandatory but cannot recognize every
unknown secret: minimize collection and review exports before sharing.

Fixes reject symlink/reparse paths, changed inputs and existing destinations. They require
interactive confirmation and an intent audit before mutation. The initial backup preserves
the original. A crash/disk failure can leave a partial backup or intent-only audit; retain
the original, inspect the audit, and retry with a new plan. Concurrent malicious filesystem
replacement by another process running as the same user is outside this tool's isolation
boundary. There is no automatic elevation or security-setting modification.

Do not run this development tool as Administrator. Do not add arbitrary command execution,
recursive deletion or automatic registry/PATH/proxy edits to the diagnostic context.
