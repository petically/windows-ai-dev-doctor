"""Explicit registration of the trusted built-in diagnostic modules."""

from ai_dev_doctor.core.engine import Check, Registry
from ai_dev_doctor.diagnostics.ai_apps import (
    chatgpt_check,
    codex_cli_check,
    codex_environment_check,
)
from ai_dev_doctor.diagnostics.developer_tools import (
    git_check,
    git_config_check,
    git_repository_check,
    github_auth_check,
    github_cli_check,
    node_check,
    npm_check,
    npx_check,
    pip_check,
    py_launcher_check,
    python_check,
    version_manager_check,
)
from ai_dev_doctor.diagnostics.environment import (
    developer_environment_check,
    executable_shadowing_check,
    path_check,
)
from ai_dev_doctor.diagnostics.network import (
    adapter_check,
    dns_check,
    https_check,
    listener_check,
    proxy_check,
    proxy_layers_check,
    system_proxy_check,
    tcp_check,
    winhttp_proxy_check,
)
from ai_dev_doctor.diagnostics.system import (
    directories_check,
    disk_check,
    gpu_check,
    powershell_check,
    privilege_check,
    process_check,
    system_check,
    terminal_check,
    webview2_check,
)


def _check(
    check_id: str,
    name: str,
    category: str,
    explanation: str,
    run: object,
    network: bool = False,
) -> Check:
    from collections.abc import Callable
    from typing import cast

    from ai_dev_doctor.core.engine import Context
    from ai_dev_doctor.models import CheckResult

    return Check(
        check_id,
        name,
        category,
        explanation,
        cast(Callable[[Context], CheckResult], run),
        network,
    )


def registry() -> Registry:
    return Registry(
        (
            _check(
                "windows-system",
                "Windows system",
                "system",
                "Reads Windows edition, release, build and architecture metadata.",
                system_check,
            ),
            _check(
                "powershell",
                "PowerShell",
                "system",
                "Runs fixed noninteractive PowerShell version probes.",
                powershell_check,
            ),
            _check(
                "windows-terminal",
                "Windows Terminal",
                "system",
                "Looks for the Windows Terminal app alias and process without launching it.",
                terminal_check,
            ),
            _check(
                "windows-privilege",
                "User privilege",
                "system",
                "Reports whether the current process is elevated; elevation is not requested.",
                privilege_check,
            ),
            _check(
                "disk-space",
                "Disk space",
                "system",
                "Reads local volume capacity for system and temporary directories.",
                disk_check,
            ),
            _check(
                "important-directories",
                "Important directories",
                "system",
                "Checks read/traverse access without creating temporary files.",
                directories_check,
            ),
            _check(
                "webview2-runtime",
                "WebView2 Runtime",
                "system",
                "Uses Microsoft's documented per-user and per-machine registry keys.",
                webview2_check,
            ),
            _check(
                "gpu-adapters",
                "GPU adapters",
                "system",
                "Reads best-effort graphics adapter metadata without changing drivers.",
                gpu_check,
            ),
            _check(
                "relevant-processes",
                "Relevant processes",
                "system",
                "Enumerates relevant executable names, never command lines.",
                process_check,
            ),
            _check(
                "git-version",
                "Git version",
                "developer-tools",
                "Runs git --version through the reviewed command boundary.",
                git_check,
            ),
            _check(
                "git-config",
                "Git global configuration",
                "developer-tools",
                "Checks key presence without returning identities or helper values.",
                git_config_check,
            ),
            _check(
                "git-repository",
                "Git repository state",
                "developer-tools",
                "Summarizes porcelain status without branch or file names.",
                git_repository_check,
            ),
            _check(
                "github-cli",
                "GitHub CLI",
                "developer-tools",
                "Runs the GitHub CLI version probe with prompts disabled.",
                github_cli_check,
            ),
            _check(
                "github-auth",
                "GitHub CLI authentication",
                "developer-tools",
                "With network consent, tests the active github.com account without token output.",
                github_auth_check,
                True,
            ),
            _check(
                "python-runtime",
                "Python",
                "developer-tools",
                "Runs an isolated Python version probe and counts PATH matches.",
                python_check,
            ),
            _check(
                "python-launcher",
                "Python launcher",
                "developer-tools",
                "Runs the Windows py launcher version probe.",
                py_launcher_check,
            ),
            _check(
                "pip",
                "pip",
                "developer-tools",
                "Runs pip --version through the reviewed command boundary.",
                pip_check,
            ),
            _check(
                "node-runtime",
                "Node.js",
                "developer-tools",
                "Runs node --version and counts PATH matches.",
                node_check,
            ),
            _check(
                "npm",
                "npm",
                "developer-tools",
                "Uses node.exe with npm's adjacent CLI script; no batch execution.",
                npm_check,
            ),
            _check(
                "npx",
                "npx",
                "developer-tools",
                "Uses node.exe with npx's adjacent CLI script; no batch execution.",
                npx_check,
            ),
            _check(
                "version-managers",
                "Version managers",
                "developer-tools",
                "Detects nvm-windows, fnm and pyenv indicators conservatively.",
                version_manager_check,
            ),
            _check(
                "chatgpt-desktop",
                "ChatGPT Desktop",
                "ai-applications",
                "Best-effort process and known data-directory discovery.",
                chatgpt_check,
            ),
            _check(
                "codex-cli",
                "Codex CLI",
                "ai-applications",
                "Runs only the Codex version probe; no authentication commands.",
                codex_cli_check,
            ),
            _check(
                "codex-environment",
                "Codex environment",
                "ai-applications",
                "Checks configuration metadata without reading file contents.",
                codex_environment_check,
            ),
            _check(
                "path-structure",
                "PATH structure",
                "environment",
                "Checks Windows PATH structure without editing or remote traversal.",
                path_check,
            ),
            _check(
                "developer-environment",
                "Developer environment",
                "environment",
                "Checks selected non-secret developer path variables without displaying values.",
                developer_environment_check,
            ),
            _check(
                "executable-shadowing",
                "Executable shadowing",
                "environment",
                "Counts local PATH matches; multiple installations alone are informational.",
                executable_shadowing_check,
            ),
            _check(
                "proxy-environment",
                "Proxy environment",
                "network",
                "Inspects proxy variables while omitting credentials, hosts and bypass lists.",
                proxy_check,
            ),
            _check(
                "proxy-system",
                "Windows system proxy",
                "network",
                "Reads current-user WinINET proxy configuration.",
                system_proxy_check,
            ),
            _check(
                "proxy-winhttp",
                "WinHTTP proxy",
                "network",
                "Uses WinHttpGetDefaultProxyConfiguration and frees API memory.",
                winhttp_proxy_check,
            ),
            _check(
                "network-adapters",
                "Network adapters and route",
                "network",
                "Uses IP Helper APIs for adapters and best-route selection.",
                adapter_check,
            ),
            _check(
                "localhost-listeners",
                "Localhost listeners",
                "network",
                "Reads IPv4 TCP listener ownership for a fixed port list.",
                listener_check,
            ),
            _check(
                "proxy-layers",
                "Proxy and tunnel layers",
                "network",
                "Correlates proxies, listeners and possible tunnel adapters conservatively.",
                proxy_layers_check,
            ),
            _check(
                "network-dns",
                "DNS connectivity",
                "network",
                "Opt-in resolution of fixed public targets with deadlines.",
                dns_check,
                True,
            ),
            _check(
                "network-tcp",
                "TCP connectivity",
                "network",
                "Opt-in TCP 443 connectivity to fixed public targets.",
                tcp_check,
                True,
            ),
            _check(
                "network-https",
                "HTTPS connectivity",
                "network",
                "Opt-in verified TLS HEAD probes with no redirects.",
                https_check,
                True,
            ),
        )
    )
