"""Pure parsers shared by diagnostics and fixture-based tests."""

import ntpath
import re
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit


def parse_git_version(output: str) -> str | None:
    match = re.fullmatch(r"git version (\d+\.\d+(?:\.\d+)?(?:\.[A-Za-z0-9]+)*)\s*", output)
    return match[1] if match else None


def analyze_path(value: str, exists: Callable[[str], bool | None]) -> tuple[tuple[str, str], ...]:
    findings: list[tuple[str, str]] = []
    seen: set[str] = set()
    for entry in value.split(";"):
        if not entry:
            findings.append(("empty", "Empty entry can cause current-directory lookup"))
            continue
        cleaned = entry.strip().strip('"')
        if '"' in entry or entry != entry.strip():
            findings.append(("quoting", entry))
        if not ntpath.isabs(cleaned) or not ntpath.splitdrive(cleaned)[0]:
            findings.append(("relative", entry))
        canonical = ntpath.normcase(ntpath.normpath(cleaned))
        if canonical in seen:
            findings.append(("duplicate", entry))
        seen.add(canonical)
        if cleaned.startswith(("\\\\", "//")):
            findings.append(("uninspected", "Remote PATH entry omitted; no share access attempted"))
            continue
        present = exists(cleaned)
        if present is None:
            findings.append(("uninspected", "Remote, relative or reparse PATH entry not traversed"))
        elif not present:
            findings.append(("missing", entry))
    return tuple(findings)


@dataclass(frozen=True)
class ProxyEndpoint:
    scheme: str
    host: str
    port: int


def parse_proxy(value: str) -> ProxyEndpoint | None:
    try:
        parsed = urlsplit(value if "://" in value else "http://" + value)
        if parsed.scheme not in ("http", "https", "socks5", "socks5h") or not parsed.hostname:
            return None
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            return None
        if any(c.isspace() for c in parsed.hostname):
            return None
        port = (
            parsed.port
            if parsed.port is not None
            else {"http": 80, "https": 443, "socks5": 1080, "socks5h": 1080}[parsed.scheme]
        )
        if not 1 <= port <= 65535:
            return None
        return ProxyEndpoint(parsed.scheme, parsed.hostname, port)
    except ValueError:
        return None


def parse_version_token(output: str) -> str | None:
    """Extract one conventional dotted version without returning surrounding output."""
    match = re.fullmatch(
        r"(?:v|Python |pip |gh version |codex-cli )?(\d+\.\d+(?:\.\d+){0,2})"
        r"(?: \([^\r\n]*\)| from [^\r\n]+)?"
        r"(?:\r?\nhttps://github\.com/cli/cli/releases/tag/v[\d.]+)?\s*",
        output,
    )
    return match[1] if match else None


@dataclass(frozen=True)
class RepositoryState:
    tracked_changes: int
    untracked: int
    conflicts: int
    branch_known: bool


def parse_git_status(output: str) -> RepositoryState | None:
    tracked = 0
    untracked = 0
    conflicts = 0
    branch_known = False
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# branch."):
            branch_known = True
        elif line.startswith(("1 ", "2 ")):
            tracked += 1
        elif line.startswith("u "):
            tracked += 1
            conflicts += 1
        elif line.startswith("? "):
            untracked += 1
        elif not line.startswith("#"):
            return None
    return RepositoryState(tracked, untracked, conflicts, branch_known)


def parse_windows_proxy(value: str) -> tuple[ProxyEndpoint, ...] | None:
    """Parse WinINET/WinHTTP single or per-scheme proxy server lists."""
    endpoints: list[ProxyEndpoint] = []
    for raw in value.split(";"):
        item = raw.strip()
        if not item:
            continue
        scheme = ""
        target = item
        if "=" in item:
            scheme, target = item.split("=", 1)
            scheme = scheme.casefold()
            if scheme not in ("http", "https", "socks", "socks5"):
                return None
        prefix = "socks5://" if scheme in ("socks", "socks5") else f"{scheme}://" if scheme else ""
        endpoint = parse_proxy(prefix + target)
        if endpoint is None:
            return None
        endpoints.append(endpoint)
    return tuple(endpoints) if endpoints else None
