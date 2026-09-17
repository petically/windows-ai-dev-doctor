"""Defense in depth: collect less, then sanitize every output surface."""

import re
from collections.abc import Mapping
from dataclasses import dataclass

SENSITIVE = re.compile(
    r"token|secret|password|passwd|api[_-]?key|authorization|credential|cookie|session|connection[_ -]?string|private[_-]?key|access[_-]?key|\bpwd\b|\buid\b",
    re.I,
)
MASK = "[REDACTED]"


@dataclass(frozen=True)
class Redactor:
    known_secrets: tuple[str, ...] = ()
    home: str = ""

    @classmethod
    def from_environment(cls, env: Mapping[str, str], home: str) -> "Redactor":
        return cls(tuple(v for k, v in env.items() if SENSITIVE.search(k) and v), home)

    def text(self, value: str) -> str:
        # Remove ANSI/OSC sequences before matching split or decorated secrets.
        value = re.sub(r"\x1b\][^\x07]*(?:\x07|\x1b\\)", "", value)
        value = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", value)
        value = "".join(
            c for c in value if c in "\n\t" or (ord(c) >= 32 and not 127 <= ord(c) <= 159)
        )
        # A Cookie header can contain multiple values; redact the whole header,
        # not just the first semicolon-delimited credential.
        value = re.sub(
            r"(?im)(\b(?:authorization|proxy-authorization|cookie|set-cookie)\s*:\s*)[^\r\n]*",
            lambda m: m[1] + MASK,
            value,
        )
        # TOML multiline strings must be consumed before ordinary quoted assignments.
        for quote in ('"' * 3, "'" * 3):
            value = re.sub(
                r"(?is)([\w.-]*(?:token|secret|password|api[_-]?key)[\w.-]*\s*=\s*)"
                + quote
                + r".*?(?:"
                + quote
                + r"|$)",
                lambda m: m[1] + MASK,
                value,
            )
        # Folded headers and indented YAML block scalars carry secrets on later lines.
        value = re.sub(
            r"(?im)(\b(?:authorization|proxy-authorization|cookie|set-cookie)\s*:\s*)[^\r\n]*(?:\n[ \t]+[^\n]*)*",
            lambda m: m[1] + MASK,
            value,
        )
        value = re.sub(
            r"(?im)([\w.-]*(?:token|secret|password|api[_-]?key|private[_-]?key)[\w.-]*\s*:\s*)[|>][-+]?[^\n]*(?:\n[ \t]+[^\n]*)*",
            lambda m: m[1] + MASK,
            value,
        )
        for secret in sorted(self.known_secrets, key=len, reverse=True):
            value = value.replace(secret, MASK)
        value = re.sub(r"(?i)\b(?:bearer|basic)\s+[^\s,;]+", MASK, value)
        value = re.sub(
            r"""(?ix)([\w.-]*(?:token|secret|password|passwd|api[_-]?key|authorization|credential|cookie|session|connection[_ -]?string|private[_-]?key|access[_-]?key|\bpwd\b|\buid\b)[\w.-]*["']?\s*[:=]\s*)(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\r\n,;]+)""",
            lambda m: m[1] + MASK,
            value,
        )
        value = re.sub(
            r"(?i)\b(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]+)\b",
            MASK,
            value,
        )
        value = re.sub(r"(?i)([a-z][a-z0-9+.-]*)://[^\s/@]+@", r"\1://[REDACTED]@", value)
        value = re.sub(r"(?i)((?:[a-z][a-z0-9+.-]*)://[^\s?#]+)[?#][^\s]*", r"\1[REDACTED]", value)
        value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", MASK, value)
        if self.home:
            for home in sorted(
                {self.home, self.home.replace("\\", "/"), self.home.replace("\\", "\\\\")},
                key=len,
                reverse=True,
            ):
                value = re.sub(re.escape(home), "[HOME]", value, flags=re.I)
        value = re.sub(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)",
            MASK,
            value,
        )
        value = re.sub(r"\\\\[^\s\"'<>]+", "[PATH]", value)
        # Unknown absolute paths can identify users outside the current profile too.
        value = re.sub(r"(?i)\b[a-z]:[\\/][^\r\n\"'<>|,;]*", "[PATH]", value)
        value = re.sub(r"(?<![\w:/])/(?!/)[^\s\"'<>;,]+", "[PATH]", value)
        return value

    def clean(self, value: object) -> object:
        if isinstance(value, Mapping):
            return {
                self.text(str(k)): MASK if SENSITIVE.search(str(k)) else self.clean(v)
                for k, v in value.items()
            }
        if isinstance(value, (tuple, list)):
            return [self.clean(v) for v in value]
        if isinstance(value, str):
            return self.text(value)
        if value is None or isinstance(value, (bool, int, float)):
            return value
        raise TypeError("Unsupported output value")
