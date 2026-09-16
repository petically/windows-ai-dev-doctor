# Engineering agent handoff

Read SPEC.md, ARCHITECTURE.md and ROADMAP.md before editing. The original complete product
brief is retained in the repository. Phase 1 intentionally implements representative checks,
not every full-product acceptance criterion. Do not publish a tag/release without authorization.
Use existing origin; never create a duplicate repository, force-push or rewrite published history.

## Development

Python 3.12+; standard-library runtime only; source under `src/ai_dev_doctor`.
Create `.venv`, then `python -m pip install -e ".[dev]"`.
Run `python -m pytest`, `python -m ruff check .`, `python -m ruff format --check .`,
and `python -m mypy src tests` before implementation commits. Windows packaging:
`python -m pip install -e ".[build]"`, then
`python -m PyInstaller --clean --noconfirm ai-dev-doctor.spec`.
Smoke-test dist/ai-dev-doctor.exe with help/version/diagnose --json/report.
Diagnostic exit 1 is a valid unhealthy host outcome; 2 indicates invocation/runtime failure.

## Architecture and standards

Use typed, small modules, frozen data models, protocols at IO boundaries and injected fakes.
CLI owns composition, engine owns isolation, plugins own interpretation, reporting owns
presentation. Do not add dependencies without a concrete benefit. Keep IDs/schema stable.
Use enum status/severity, structured evidence and conservative findings. Never fabricate PASS.
Do not parse localized human-readable Windows output when a structured API is available.

## Add a diagnostic

1. Add a pure parser if useful and a callable accepting Context; register a Check explicitly.
2. Return validated CheckResult with matching identity and minimal evidence. No raw config,
   environment or command dumps. No subprocess/socket/write calls in diagnostic plugins.
3. Add any IO to the reviewed adapter and declare network use. Ordinary diagnostics stay
   offline unless the user passes --network. Hard time/output bounds are mandatory.
4. Test pass, failure, missing/denied/malformed cases and uncertainty; use fakes, not live network.
5. Update explain text, docs, coverage table and roadmap. Review output for sensitive data.

## Add a fix

Keep plan/confirm/execute separate. Default NO; dry-run must not create anything. Only exact,
proven targets; reject symlinks/reparse ancestors, changed inputs and collisions. Recheck after
confirmation. Prefer exclusive backup/rename and give recovery instructions. Log intent and
outcome. Test refusal, dry-run, drift, collisions, successful action and failed audit. No generic
arbitrary-file deletion/command execution interface. Uncertain repairs remain manual guidance.

## Security invariants

Never expose API keys/tokens/cookies/credentials or personal paths in reports/logs. Redaction
is centralized and mandatory on every output path. Add canary tests for new evidence types.
Never use shell=True, run arbitrary command strings, silently alter PATH/proxy/registry,
terminate unrelated processes, auto-elevate, disable security tools or change drivers.
No telemetry/uploads. Explicit local exports/logging are opt-in; never overwrite user files.
No secrets, machine paths, generated reports, caches, virtualenvs or builds in commits.
Review `git status`, staged diff and `git diff --check`; commit logical milestones and push.
Do not add sub-agents or parallel agent instructions merely to work around task constraints.
