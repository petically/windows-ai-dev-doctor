# Contributing

Read SPEC.md and ARCHITECTURE.md first. AGENTS.md contains exact development commands
and extension recipes for diagnostics and fixes. Open an issue for a proposed feature,
false positive or behavior change; keep pull requests focused.

Use Python 3.12+, type hints and injected adapters. Run pytest, Ruff lint/format checks,
and strict mypy before submitting. A diagnostic needs success, missing/denied/malformed
and uncertainty tests. Tests must not require live internet or your installed tools.
Use synthetic fixtures; never attach raw private reports, tokens or application configs.

Maintain the stable check IDs and report schema. Document limitations and uncertain
inferences. Repairs need explicit confirmation, precondition revalidation, backup/recovery,
audit and refusal-path tests. Prefer manual guidance over unsafe automation.

By contributing, you agree that contributions are licensed under this repository's MIT license.
Follow CODE_OF_CONDUCT.md. Security reports belong in the private channel described in SECURITY.md.
