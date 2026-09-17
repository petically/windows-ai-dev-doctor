# Phase 3 release-readiness evidence

## Scope and decisions

Reviewed the existing main branch, including Phase 2 commits 8875a46 and 59189b4, against
SPEC, ARCHITECTURE, AGENTS, the original product brief and the authorized Phase 3 instructions.
The review covered every source module, existing test module, workflow and packaging entry point.
No runtime dependency was added. The 36 IDs and report schema 1 remain stable.

v0.1.0 uses a complete unsigned portable x64 ZIP plus SHA-256 checksum. The executable and
_internal runtime directory must stay together. Signing and an installer are deferred; no
certificate or installer safety is implied. Windows reputation/SmartScreen warnings may occur.

## Findings and resolution

| Area | Verified issue and change | Regression evidence |
| --- | --- | --- |
| Process lifecycle | Direct-child timeout left descendants alive; atomically assign Windows Job at creation, close on normal exit/timeout/cancel, refuse job setup failure | Real descendant and unrelated-sentinel processes, output flood, Unicode argv, cancellation and job refusal |
| Win32 | Unvalidated TCP row count, LAN-only listeners treated as localhost, unbounded adapter size/pointers | Malformed/truncated TCP fixtures, address/state filters, real host API smoke, x64 ABI layout assertions |
| Privacy | Escaped/multiline credentials, non-HTTP URI userinfo, connection strings, private keys and other personal paths | Canary corpus through JSON/HTML/terminal/log surfaces |
| False findings | Optional apps/config, absent global identity, inactive proxy and IPv6 observations overstated | Optional-tool, configuration error, unknown process, inactive/IPv6/localhost proxy and IPv4-route tests |
| Read-only probes | Git status could refresh index/use fsmonitor | Fixed no-optional-locks/fsmonitor-disabled/submodule-ignored invocation |
| Fixes | Reviewed backup-only operation; no destructive cache repair added | Default-NO, noninteractive refusal, dry-run, drift before/after audit, collisions, reparse paths, success and audit failures |
| Network | Empty DNS result could pass; unavailable IPv4 evidence overstated | Empty DNS, worker deadline, DNS/TCP/TLS/HTTP failures, fixed multiple targets and consent tests |
| Packaging | Smoke ran in source tree; redirected Chinese path output used legacy encoding; absent PE metadata; wildcard Markdown packaging | Relocated complete bundle, Unicode/spaces, UTF-8 output, metadata, explicit manifest, export collision |
| CI | Phase 2 Linux mypy failed on Windows-only APIs | Explicit platform guards; strict checks for Windows and Linux, Windows 2022/2025 matrix |

## Diagnostic coverage reviewed

| Category | All stable IDs reviewed | Remaining interpretation limits |
| --- | --- | --- |
| System | windows-system, powershell, windows-terminal, windows-privilege, disk-space, important-directories, webview2-runtime, gpu-adapters, relevant-processes | Metadata is not application/driver health; no elevation; registry/Store evidence can be incomplete |
| Developer tools | git-version, git-config, git-repository, github-cli, github-auth, python-runtime, python-launcher, pip, node-runtime, npm, npx, version-managers | Trusted installed tools; version launch success only; global identity key presence; stored gh account only; batch launchers not executed |
| AI applications | chatgpt-desktop, codex-cli, codex-environment | Presence and bounded metadata; no proprietary internals or cache-health inference |
| Environment | path-structure, developer-environment, executable-shadowing | Remote/reparse paths omitted; duplicates/installations alone do not prove failure |
| Network | proxy-environment, proxy-system, proxy-winhttp, network-adapters, localhost-listeners, proxy-layers, network-dns, network-tcp, network-https | Direct fixed-target probes require consent; IPv4 correlation only; no proxy-path or automatic-discovery validation |

## Validation record

Local host: Windows 11 x64 build 26200, Python 3.12.10. Tests use synthetic state and bounded
owned child processes, with no live network requirement. Client Windows 10 and a clean client
Windows 11 VM have **not** been tested. This developer host is not a clean-machine substitute.
Server CI images are also not equivalent to Windows client validation.

- Baseline independently reproduced: 101 passed, 1 skipped.
- Current local regression suite: 142 passed, 1 skipped (OS symbolic-link creation privilege).
  Reparse-attribute refusal remains exercised independently of that skip.
- Ruff, formatting, strict mypy (Windows and Linux platform modes), source credential/path scan,
  sdist/wheel, Windows executable and relocated smoke passed before the review commit.
- Review commit `5006133` passed all six Windows 2022/2025 and Ubuntu Python 3.12/3.13 jobs,
  plus Windows build and relocated smoke: [CI evidence](https://github.com/petically/windows-ai-dev-doctor/actions/runs/35177095322).
- Release preparation updates version/PE metadata to 0.1.0 and repeats all local gates.
  The final CI run and immutable release-commit hash are recorded in GitHub Release notes;
  no tag or release is published until that exact commit passes CI.

## Known validation requirements and limits

1. Test clean Windows 10/11 x64 clients as standard users, including non-English UI, no Python,
   missing optional tools, protected directories, offline use and enterprise restrictions.
2. Store alias/reparse discovery is intentionally conservative. WebView2 fixed runtimes and
   application-specific internal corruption are not diagnosed. ARM64 is unvalidated.
3. IPv6 listener ownership and routing, localhost name resolution and automatic proxy discovery
   are not evaluated; no conflict is inferred from those missing observations.
4. Installed executables/plugins remain trusted. Job ownership controls lifetime, not filesystem
   or network access. Local filesystem/API calls still depend on OS responsiveness.
5. Redaction and source pattern scans are defense in depth, not proof against all opaque secrets.
6. Backup keeps the source intact; restore is manual. Concurrent malicious same-user replacement,
   disk loss and partial writes remain documented boundaries. Cache repairs remain manual.

## API references checked

- [Atomic job assignment before initial execution](https://devblogs.microsoft.com/oldnewthing/20230209-00/?p=107812)
- [Windows process attribute lists](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute)
- [TCP table layout](https://learn.microsoft.com/en-us/windows/win32/api/tcpmib/ns-tcpmib-mib_tcptable_owner_pid)
- [GitHub supported runner images](https://github.com/actions/runner-images)
