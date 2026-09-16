# Roadmap

## Phase 1 — foundation (current)

Architecture and safety contracts; Python package/CLI; registry and immutable results;
bounded command/network boundaries; strict configuration; mandatory redaction; local
reports/logging; representative diagnostics; confirmed config backup; tests and CI;
Windows development artifact build. No production release or v0.1.0 tag.

## Phase 2 — diagnostic depth

1. Add Windows API adapter (read-only registry, privilege, platform paths); PowerShell,
   Terminal, disk/temp inspection without write probes; robust WebView2 discovery.
2. Add gh version/auth (explicit network consent), Python/pip/launcher, Node/npm/npx and
   version managers; executable shadowing; Git config/repository state without identities.
3. Add system/WinHTTP proxy, adapters/routes, multiple DNS targets, localhost/listeners and
   ownership; distinguish direct and proxy-aware connectivity, avoid false conflict claims.
4. Add best-effort ChatGPT/Codex discovery and configuration metadata, process/GPU adapters,
   cache evidence with uncertainty; never parse proprietary formats speculatively.
5. Expand localized/permission-denied fixtures and Windows 10/11 packaged validation.
6. Consider app-specific fixes only after discovery, process guards and recovery are tested.

## Release readiness

Audit all original acceptance criteria; expand threat-model/redaction corpus; review false
positives; verify standalone distribution on clean Windows machines; document limitations;
validate install instructions. Only then request/act on release authorization for v0.1.0.
