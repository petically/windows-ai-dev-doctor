# Project: Windows AI Dev Doctor

You are the lead engineer, product designer, QA engineer, security reviewer, technical writer, and release engineer for this project.

Your task is to autonomously design, implement, test, document, package, and polish a production-quality open-source Windows developer diagnostic tool called:

# Windows AI Dev Doctor

The project should be suitable for publishing publicly on GitHub.

Do not stop after creating a prototype or minimal demo.

Continue working autonomously until the project satisfies the acceptance criteria defined below.

You may refactor your own implementation whenever necessary.

When something is unclear, make a reasonable engineering decision instead of waiting for user input, unless the missing information makes implementation genuinely impossible.

---

# 1. Product Goal

Windows AI Dev Doctor is a diagnostic and repair assistant for Windows users who work with:

- ChatGPT Desktop
- Codex
- AI coding agents
- Git
- GitHub CLI
- Node.js
- Python
- PowerShell
- Windows Terminal
- WebView2
- GPU-accelerated desktop applications
- HTTP/HTTPS APIs
- system proxies
- VPN/TUN/proxy software
- DNS
- developer environment variables

Its purpose is to answer:

> "Why is my AI/developer tool not working correctly on Windows?"

Examples:

- ChatGPT Desktop freezes when moving the mouse.
- Codex cannot connect to the internet.
- GitHub CLI authentication is broken.
- Node or Python is missing from PATH.
- system proxy and TUN configuration conflict.
- DNS resolution is failing.
- WebView2 is missing or corrupted.
- an application cache may be corrupted.
- Git configuration is incorrect.
- HTTPS connectivity is broken.
- environment variables point to invalid paths.
- localhost ports are unexpectedly occupied.
- a required process is repeatedly crashing.
- a developer tool exists but cannot be executed.
- multiple versions of Python/Node/Git create conflicts.

The program should diagnose problems clearly and propose safe corrective actions.

---

# 2. Core Product Principles

Prioritize:

1. Safety
2. Readability
3. Explainability
4. Reliability
5. Reversibility
6. Minimal dependencies
7. Useful diagnostics instead of superficial checks
8. Professional open-source project quality

Never perform destructive system modifications automatically.

Any repair operation must be:

- explicit
- explained
- reversible where reasonably possible
- confirmed by the user before execution
- logged

Diagnostic mode must never modify the system.

---

# 3. Primary Interfaces

The first release must include a professional CLI.

Example:

```powershell
ai-dev-doctor diagnose
```

Expected output:

```text
Windows AI Dev Doctor
Version 1.0.0

System
✓ Windows 11 detected
✓ PowerShell available
✓ WebView2 Runtime detected

Developer Tools
✓ Git 2.x
✓ GitHub CLI installed
⚠ GitHub CLI authentication requires attention
✓ Node.js 22.x
✓ Python 3.x

Network
✓ DNS resolution
✓ HTTPS connectivity
⚠ System proxy detected
⚠ Possible proxy/TUN configuration conflict

AI Applications
✓ ChatGPT Desktop detected
✓ Codex configuration directory detected
⚠ GPU cache appears unusually large or stale

Environment
✓ PATH structure valid
⚠ Multiple Python installations detected

Summary

Passed: 18
Warnings: 4
Failed: 1

Recommended actions:

1. Reauthenticate GitHub CLI.
2. Review system proxy configuration.
3. Inspect GPU cache state.

Run:

ai-dev-doctor explain github-auth

for more information.
```

Also implement:

```powershell
ai-dev-doctor diagnose
ai-dev-doctor diagnose --verbose
ai-dev-doctor diagnose --json
ai-dev-doctor diagnose --category network
ai-dev-doctor explain <check-id>
ai-dev-doctor fix <fix-id>
ai-dev-doctor fix --dry-run <fix-id>
ai-dev-doctor report
ai-dev-doctor report --output report.json
ai-dev-doctor report --output report.html
ai-dev-doctor version
ai-dev-doctor help
```

If technically reasonable, also support:

```powershell
ai-dev-doctor doctor
```

as an alias of `diagnose`.

---

# 4. Technology Choice

Choose a technology stack suitable for:

- Windows 10/11
- fast startup
- easy distribution
- readable code
- maintainability
- filesystem/process/network inspection
- automated testing
- GitHub Actions
- standalone executable packaging

Preferred implementation:

Python 3.12+

unless there is a compelling engineering reason to choose Rust.

If Python is selected, produce a distributable standalone Windows executable so end users do not need to install Python.

Suggested libraries may include lightweight mature libraries such as:

- typer or click
- rich
- psutil
- pydantic

Avoid unnecessarily large frameworks.

Do not introduce Electron.

Keep dependencies minimal.

---

# 5. Architecture

Design the codebase using modular diagnostics.

For example:

```text
src/
  ai_dev_doctor/
    cli/
    core/
    diagnostics/
      system/
      network/
      developer_tools/
      ai_apps/
      environment/
    fixes/
    reporting/
    models/
    utilities/
```

Each diagnostic check should be independently testable.

Use a consistent internal result model similar to:

```text
id
name
category
status
summary
details
severity
evidence
recommendations
fix_ids
documentation_url
```

Status values should include something equivalent to:

```text
PASS
INFO
WARNING
FAIL
SKIPPED
ERROR
```

A failure in one diagnostic must not crash the entire program.

---

# 6. Diagnostics to Implement

Implement meaningful checks for the following areas.

## 6.1 Windows System

Detect:

- Windows version
- edition
- architecture
- build number
- PowerShell availability/version
- Windows Terminal availability if present
- current user privilege level
- available disk space
- temporary directory accessibility
- important environment directories

Do not require Administrator privileges for ordinary diagnostics.

Clearly identify checks that would benefit from elevated permissions.

---

# 6.2 Git

Check:

- Git installed
- executable location
- version
- `git --version`
- global username
- global email
- default branch configuration
- credential helper
- suspicious duplicate Git installations
- repository status when launched inside a Git repository

Never expose credentials.

---

# 6.3 GitHub CLI

Check:

- `gh` installed
- version
- executable path
- authentication state

Use safe CLI commands.

Never print access tokens.

Explain how authentication problems can be resolved.

---

# 6.4 Python

Check:

- python
- py launcher
- pip
- version
- PATH location
- multiple installations
- virtual environment state
- common PATH conflicts

Do not treat multiple Python installations as automatically wrong.

Explain why it may or may not be a problem.

---

# 6.5 Node.js

Check:

- node
- npm
- npx
- version
- executable location
- multiple installations
- common PATH conflicts

If available, identify version managers such as:

- nvm-windows
- fnm

without assuming their existence.

---

# 6.6 WebView2

Check whether Microsoft Edge WebView2 Runtime is installed.

Use robust detection methods.

If multiple detection methods exist, document your choice.

Do not perform WebView2 installation automatically.

Provide guidance instead.

---

# 6.7 ChatGPT Desktop

Implement best-effort detection of ChatGPT Desktop installations.

Potentially inspect:

- installed application information
- known installation directories
- running processes
- application data directories

Avoid relying on a single hardcoded path.

Diagnostic checks may include:

- installation detected
- running process detected
- application data directory exists
- cache directory accessible
- suspiciously large cache
- unusually old/stale cache indicators where meaningful

Do not delete application data automatically.

Do not make undocumented assumptions about proprietary internal formats.

If a check cannot be performed reliably, report it as informational rather than pretending certainty.

---

# 6.8 Codex

Detect, where reasonably possible:

- Codex CLI availability
- executable path
- version
- common configuration directories
- configuration readability
- repository environment
- Git integration
- shell availability

Never expose:

- API keys
- access tokens
- secrets
- credentials

When reading configuration files, redact sensitive values.

Create a reusable secret-redaction layer.

Sensitive keys include patterns such as:

```text
token
secret
password
passwd
api_key
apikey
authorization
credential
cookie
session
```

---

# 6.9 Network

Implement useful network diagnostics.

Check:

- network adapter availability
- default route
- DNS resolution
- HTTPS connectivity
- TCP connectivity
- system proxy
- WinHTTP proxy
- environment proxy variables
- localhost connectivity

Distinguish clearly between:

- DNS failure
- TCP failure
- TLS/HTTPS failure
- HTTP application failure

Do not simply report "network failed".

Use reasonable timeout values.

Diagnostics must not hang indefinitely.

---

# 6.10 Proxy / VPN / TUN

Inspect:

- Windows system proxy
- WinHTTP proxy
- HTTP_PROXY
- HTTPS_PROXY
- ALL_PROXY
- NO_PROXY

Where possible, identify likely VPN/TUN adapters.

Do not assume that having a proxy or TUN adapter is bad.

Instead detect potentially conflicting configurations such as:

- proxy points to unavailable localhost port
- environment proxy differs significantly from system proxy
- proxy configured but listener absent
- multiple proxy layers likely active

Phrase findings conservatively:

"Possible conflict detected"

rather than:

"This configuration is broken"

unless evidence supports that conclusion.

---

# 6.11 DNS

Check resolution of several stable domains.

Use multiple targets so one unavailable domain does not create a false diagnosis.

Report:

- resolved addresses
- elapsed time where practical
- errors

Do not use DNS tests that leak unnecessary user information.

---

# 6.12 HTTPS

Perform safe GET or HEAD requests to a small number of stable endpoints.

Do not rely exclusively on OpenAI endpoints.

Categorize failures.

Support configurable timeout.

---

# 6.13 PATH

Analyze PATH.

Detect:

- nonexistent entries
- duplicate entries
- malformed entries
- suspicious quoting
- Git/Python/Node executable shadowing
- excessively duplicated directories

Do not modify PATH automatically in diagnose mode.

Provide detailed evidence.

---

# 6.14 Environment Variables

Inspect developer-related environment variables.

Never display secrets.

Highlight malformed or nonexistent paths.

Implement robust secret redaction.

---

# 6.15 Processes

Provide safe process inspection.

Look for relevant processes such as:

- ChatGPT
- git
- node
- python
- proxy clients
- known developer tools

Do not terminate processes during diagnostics.

---

# 6.16 Ports

Inspect common localhost proxy and developer ports.

Show listeners when useful.

Avoid claiming a port conflict merely because it is occupied.

Explain which process owns a port if permissions allow.

---

# 6.17 GPU / Graphics Diagnostics

Provide best-effort diagnostics without unsafe driver manipulation.

Check:

- GPU adapter name
- driver information where available
- hardware acceleration environment indicators
- DirectX-related information if accessible through safe Windows APIs or commands

Optionally inspect application cache directories related to GPU acceleration if reliably identifiable.

Do NOT automatically delete caches.

Provide a safe fix mechanism only if:

- the exact directory is known,
- deletion is generally safe,
- the application is not running,
- the user explicitly confirms.

Prefer renaming/backup before deletion when feasible.

---

# 7. Fix Framework

Implement a generic fix framework.

Example:

```powershell
ai-dev-doctor fix clear-chatgpt-gpu-cache
```

Before any change, show:

```text
Action:
Rename the ChatGPT GPU cache directory.

Reason:
The cache appears stale and may contribute to rendering problems.

Risk:
Low.

Reversible:
Yes.

Original:
...

Backup:
...

Proceed? [y/N]
```

Default must always be NO.

Implement:

```powershell
ai-dev-doctor fix --dry-run <fix-id>
```

Dry-run must show exactly what would happen without changing anything.

Possible safe fixes may include:

- creating backup of a configuration file
- removing obviously invalid duplicate PATH entries only if implemented very carefully
- clearing or renaming known noncritical caches
- resetting selected safe application caches
- generating commands for manual fixes

However:

When uncertain, do NOT implement automatic repair.

Instead provide manual remediation instructions.

---

# 8. Safety Requirements

These requirements are mandatory.

Never:

- expose secrets
- print API keys
- print GitHub tokens
- print cookies
- delete arbitrary user files
- recursively delete unknown directories
- modify registry keys without explicit confirmation
- change firewall configuration automatically
- disable antivirus
- disable Windows security
- install drivers
- uninstall applications
- modify BIOS settings
- kill unrelated processes
- change proxy settings silently
- change PATH silently
- elevate privileges without explanation

All state-changing operations must be explicit.

Create a centralized safety layer for operations.

---

# 9. Privacy

The tool should work primarily offline.

No telemetry by default.

No analytics by default.

No diagnostic data should leave the user's computer unless the user explicitly exports a report.

Document this clearly.

Reports must redact secrets automatically.

Add tests specifically for secret redaction.

---

# 10. Reports

Support terminal, JSON, and HTML reports.

Example:

```powershell
ai-dev-doctor report --output doctor-report.json
```

and

```powershell
ai-dev-doctor report --output doctor-report.html
```

HTML report should be:

- self-contained
- readable
- responsive
- professional
- usable without internet access

Include:

- system summary
- diagnostic categories
- status
- evidence
- recommendations
- timestamp
- application version

Do not include secrets.

---

# 11. UI / CLI Design

Use a professional CLI presentation.

Recommended semantics:

```text
✓ PASS
ℹ INFO
⚠ WARNING
✗ FAIL
? SKIPPED
```

Support terminals that cannot display Unicode.

Use semantic colors but never rely only on color to convey meaning.

Support:

```text
NO_COLOR
```

where practical.

---

# 12. Configuration

Allow configuration using a file such as:

```text
%USERPROFILE%\.ai-dev-doctor\config.toml
```

or another reasonable standard location.

Possible settings:

```text
network_timeout
enabled_categories
disabled_checks
report_redaction
verbose
```

Provide sane defaults.

The application must work without a config file.

---

# 13. Logging

Implement structured local logging.

Logs should:

- help debugging
- redact secrets
- avoid storing unnecessary personal information

Provide:

```powershell
ai-dev-doctor diagnose --verbose
```

Never log credentials.

---

# 14. Error Handling

The application must gracefully handle:

- missing commands
- access denied
- malformed configuration
- unavailable network
- unexpected command output
- Unicode paths
- spaces in Windows paths
- non-English Windows installations

A failed diagnostic plugin must not crash the entire application.

---

# 15. Testing

Testing is mandatory.

Implement:

## Unit tests

For:

- result models
- PATH parsing
- version parsing
- secret redaction
- proxy parsing
- command execution
- configuration
- reporting
- diagnostic checks

## Integration tests

Test representative diagnostic workflows.

Mock system state where appropriate.

Do not make tests depend heavily on the developer machine.

## Security tests

Verify that values resembling secrets are redacted.

Example inputs:

```text
OPENAI_API_KEY=...
GITHUB_TOKEN=...
Authorization: Bearer ...
password=...
```

None may appear unredacted in reports or logs.

## CLI tests

Test:

```text
diagnose
explain
fix --dry-run
report
version
help
```

---

# 16. Code Quality

Use:

- type hints
- clear module boundaries
- docstrings where valuable
- linting
- formatting
- static analysis where reasonable

For Python, configure tools such as:

```text
ruff
pytest
mypy or pyright
```

Use modern `pyproject.toml`.

Avoid giant modules.

Avoid unnecessary abstraction.

Prefer clarity over cleverness.

---

# 17. GitHub Repository Quality

Prepare the repository as a polished open-source project.

Required files:

```text
README.md
LICENSE
CONTRIBUTING.md
SECURITY.md
CHANGELOG.md
CODE_OF_CONDUCT.md
AGENTS.md
ARCHITECTURE.md
ROADMAP.md
pyproject.toml
.gitignore
```

Also create:

```text
.github/
  workflows/
  ISSUE_TEMPLATE/
  PULL_REQUEST_TEMPLATE.md
```

Add issue templates for:

- Bug report
- Feature request
- Diagnostic false positive

---

# 18. README

README should look professional.

Include:

1. Project title
2. Concise description
3. Why the project exists
4. Major features
5. Screenshot/example terminal output
6. Installation
7. Usage
8. Example commands
9. Safety model
10. Privacy model
11. Diagnostic categories
12. Reporting
13. Development setup
14. Roadmap
15. Contributing
16. License

Include realistic command examples.

Do not make exaggerated claims.

Do not claim bugs are automatically fixed unless they actually are.

---

# 19. Architecture Documentation

Create:

```text
ARCHITECTURE.md
```

Explain:

- core architecture
- diagnostic plugin model
- result model
- command execution abstraction
- reporting system
- redaction system
- fix framework
- safety boundaries

Make it useful for future contributors.

---

# 20. AGENTS.md

Create a useful `AGENTS.md` for future AI coding agents.

Include:

- repository architecture
- coding standards
- test commands
- lint commands
- security constraints
- forbidden behaviors
- how to add a diagnostic
- how to add a fix
- redaction requirements

Future coding agents must understand that system modifications require strong safety precautions.

---

# 21. GitHub Actions

Create CI that runs on pull requests and pushes.

At minimum:

- lint
- formatting check
- type check
- unit tests

Test appropriate supported Python versions.

Add Windows CI because this is primarily a Windows application.

If possible also run platform-independent tests on Linux for faster feedback.

---

# 22. Packaging

Produce a Windows standalone executable.

Preferred outcome:

```text
ai-dev-doctor.exe
```

Use an established packaging approach such as PyInstaller if Python is selected.

Automate packaging through GitHub Actions.

Create a release workflow capable of producing downloadable Windows artifacts.

Do not require users to clone the repository to use the program.

---

# 23. Versioning

Use semantic versioning.

Initial production-ready milestone:

```text
v0.1.0
```

Do not call the first version `1.0.0` unless the project genuinely deserves that maturity.

Create:

```text
CHANGELOG.md
```

---

# 24. Git Workflow

Work incrementally.

Use meaningful commits.

Suggested pattern:

```text
chore: initialize project structure
feat: add diagnostic framework
feat: add Windows system diagnostics
feat: add developer tool diagnostics
feat: add network diagnostics
feat: add proxy diagnostics
feat: add AI application diagnostics
feat: add report generation
feat: add safe fix framework
test: expand diagnostic coverage
docs: complete project documentation
ci: add Windows build and release workflows
```

Do not create meaningless commits merely to increase commit count.

Do not push broken commits if avoidable.

---

# 25. Development Process

Follow this sequence.

## Phase 1

Inspect the working directory.

If the repository is empty, initialize the project.

Create:

```text
SPEC.md
ARCHITECTURE.md
ROADMAP.md
AGENTS.md
```

Before major implementation, write the architecture and product specification.

Do not stop after writing them.

Continue immediately into implementation.

---

## Phase 2

Implement the core framework:

- CLI
- diagnostic registry
- result models
- command execution
- configuration
- secret redaction
- logging

Add tests.

---

## Phase 3

Implement diagnostic categories.

Prioritize:

1. system
2. Git
3. GitHub CLI
4. Python
5. Node.js
6. network
7. DNS
8. HTTPS
9. proxy
10. PATH
11. environment
12. processes
13. ports
14. WebView2
15. ChatGPT Desktop
16. Codex
17. GPU

Add tests after each major category.

---

## Phase 4

Implement:

- explanations
- recommendations
- HTML reports
- JSON reports
- safe fix framework
- dry run

---

## Phase 5

Complete:

- documentation
- CI
- packaging
- release workflow
- issue templates
- security documentation

---

## Phase 6

Perform a full project audit.

Act as a reviewer who did not write the project.

Look for:

- bugs
- security flaws
- unsafe repair logic
- poor UX
- unclear output
- bad architecture
- unnecessary dependencies
- Windows compatibility problems
- secret leakage
- missing tests
- false-positive diagnostics
- brittle path assumptions
- localization problems
- subprocess quoting bugs
- Unicode issues

Fix all verified issues.

---

# 26. Validation

Before considering the task finished, run all relevant commands.

For example:

```powershell
pytest
ruff check .
ruff format --check .
mypy .
```

or their project equivalents.

Then build the executable.

Run basic smoke tests against the packaged executable.

Verify:

```text
ai-dev-doctor.exe --help
ai-dev-doctor.exe version
ai-dev-doctor.exe diagnose
ai-dev-doctor.exe diagnose --json
```

Verify generated reports.

---

# 27. Acceptance Criteria

The project is not finished until all of the following are true:

- application launches successfully
- diagnose command works
- diagnostics are modular
- failure of one diagnostic does not crash others
- Git detection works
- GitHub CLI detection works
- Python detection works
- Node detection works
- network checks work
- DNS checks work
- proxy inspection works
- PATH analysis works
- environment variable inspection works
- WebView2 detection exists
- ChatGPT Desktop best-effort diagnostics exist
- Codex best-effort diagnostics exist
- GPU diagnostics exist
- secret redaction is implemented
- JSON reports work
- HTML reports work
- fix dry-run works
- unsafe fixes are not automatically executed
- automated tests exist
- secret redaction tests exist
- lint passes
- tests pass
- documentation is complete
- GitHub Actions CI exists
- Windows executable can be built
- README is professional
- repository contains open-source contribution files
- no obvious secrets exist in repository
- no hardcoded personal paths exist
- no machine-specific temporary files exist
- project can reasonably be published on GitHub

---

# 28. Important Engineering Rule

Do not fake functionality.

If reliable detection is impossible:

1. implement the best evidence-based detection available,
2. clearly label uncertainty,
3. document limitations.

Never return a PASS merely because a check was difficult to implement.

Use SKIPPED or INFO where appropriate.

---

# 29. Internet Usage

Use internet access when available to verify:

- official Windows APIs
- command behavior
- packaging practices
- WebView2 detection techniques
- Git/GitHub CLI behavior

Prefer authoritative documentation.

Do not copy large amounts of third-party code.

Respect software licenses.

---

# 30. Final Review

Once implementation is complete, perform one final autonomous review.

Pretend the repository belongs to another developer and you are evaluating whether you would trust installing it on your own Windows machine.

Review:

- functionality
- safety
- privacy
- maintainability
- installation
- documentation
- code quality
- test coverage
- release readiness

Fix problems instead of merely listing them whenever feasible.

---

# 31. Final Deliverable

At completion, provide a concise summary containing:

- implemented features
- repository structure
- test results
- build result
- executable location
- known limitations
- suggested next milestones

Do not stop at planning.

Do not ask for routine confirmation.

Continue autonomously through implementation, testing, documentation, packaging, and final review.

The target is a real GitHub-quality open-source project, not a coding demonstration.