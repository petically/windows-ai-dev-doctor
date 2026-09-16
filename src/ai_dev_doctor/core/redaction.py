"""Defense in depth: collect less, then sanitize every output surface."""

import re
from collections.abc import Mapping
from dataclasses import dataclass

SENSITIVE = re.compile(
    r"token|secret|password|passwd|api[_-]?key|authorization|credential|cookie|session", re.I
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
        value = "".join(c for c in value if c in "\n\t" or (ord(c) >= 32 and ord(c) != 127))
        for secret in sorted(self.known_secrets, key=len, reverse=True):
            value = value.replace(secret, MASK)
        value = re.sub(r"(?i)\b(?:bearer|basic)\s+[^\s,;]+", MASK, value)
        value = re.sub(
            r"""(?ix)([\w.-]*(?:token|secret|password|passwd|api[_-]?key|authorization|credential|cookie|session)[\w.-]*["']?\s*[:=]\s*)(?:"[^"\r\n]*"|'[^'\r\n]*'|[^\r\n,;]+)""",
            lambda m: m[1] + MASK,
            value,
        )
        value = re.sub(
            r"(?i)\b(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]+)\b",
            MASK,
            value,
        )
        value = re.sub(r"(?i)(https?|socks5h?)://[^\s/@]+@", r"\1://[REDACTED]@", value)
        value = re.sub(r"(?i)((?:https?|socks5h?)://[^\s?#]+)[?#][^\s]*", r"\1[REDACTED]", value)
        value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", MASK, value)
        if self.home:
            for home in {self.home, self.home.replace("\\", "/")}:
                value = re.sub(re.escape(home), "[HOME]", value, flags=re.I)
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
