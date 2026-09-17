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

## Release readiness (requires review/authorization)

- Audit the original full-product acceptance criteria and the diagnostic false-positive model.
- Complete a dedicated security review of Win32 structures, process attribution, redaction
  corpus and command process-tree containment.
- Validate the standalone unsigned bundle on clean supported Windows 10 and Windows 11 systems,
  including Store-installed application layouts and restricted enterprise environments.
- Decide whether to add signed packaging/installer support and app-specific repair primitives.
- Confirm documentation and install instructions, then obtain explicit authorization before
  creating v0.1.0, a tag or a GitHub Release.
