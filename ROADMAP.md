# Roadmap

## Phase 1 — foundation (complete)

Architecture and safety contracts; Python package/CLI; registry and immutable results;
bounded command/network boundaries; strict configuration; mandatory redaction; local
reports/logging; representative diagnostics; confirmed config backup; tests and CI;
Windows development artifact build. No production release or v0.1.0 tag.

## Phase 2 — diagnostic depth (implementation complete)

1. Added the read-only Windows adapter for registry, privilege, platform paths, disk,
   WebView2, network interfaces/routes/listeners, processes, GPU and application metadata.
2. Added reviewed PowerShell, Terminal, Git/GitHub CLI, Python/pip/launcher, Node/npm/npx,
   Codex and version-manager diagnostics plus executable shadowing and repository summaries.
3. Added environment, system and WinHTTP proxy inspection; conservative proxy/listener
   correlation; and consented DNS, TCP and HTTPS stages.
4. Added best-effort ChatGPT/Codex discovery and bounded configuration/cache metadata without
   parsing proprietary contents or claiming uncertain state.
5. Expanded parser, missing/denied/malformed, privacy, command-safety and packaged smoke tests.
6. Retained the configuration backup as the only automatic fix. Application cache repair is
   intentionally manual because reliable ownership, running-process and rollback guarantees
   are not yet proven.

## Phase 3 - release readiness completed

- Independent review of all adapters, diagnostics, reporting and the backup framework.
- Atomic Windows Job containment, robust TCP table bounds, conservative discovery and
  proxy correlation, expanded privacy regression coverage and UTF-8 redirected output.
- Windows Server 2022/2025 CI, fixed Linux type-check guards and strengthened relocated
  portable-bundle smoke tests. Validation results are tracked in RELEASE_READINESS.md.
- Release choice: unsigned portable x64 ZIP, versioned PE metadata and SHA-256 checksum.
  Installer and signing are deferred; commercial signing is not required for v0.1.0.
- Review commit 5006133 passed all six platform/Python CI jobs and Windows portable packaging.
  Release preparation sets 0.1.0; final publication requires green CI on that exact commit.

## Next validation and development

- Clean Windows 10 and clean Windows 11 client validation under standard-user accounts.
- Enterprise access controls, Store layouts, ARM64 and IPv6 listener/route evidence.
- Signed distribution once certificate ownership and maintenance are available.
- Installer only if it adds sufficient value beyond the portable bundle.
- Application cache repair remains manual until ownership, running-process protection,
  backup and rollback can be demonstrated; no destructive cache repair by default.
