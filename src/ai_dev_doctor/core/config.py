"""Strict bounded configuration. Redaction and network consent are not configurable."""

import math
import tomllib
from dataclasses import dataclass
from pathlib import Path

CATEGORIES = ("system", "developer-tools", "environment", "network")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    network_timeout: float = 4.0
    command_timeout: float = 4.0
    enabled_categories: tuple[str, ...] = CATEGORIES
    disabled_checks: tuple[str, ...] = ()
    verbose: bool = False


def config_path() -> Path:
    return Path.home() / ".ai-dev-doctor" / "config.toml"


def parse_config(data: bytes) -> Config:
    if len(data) > 65536:
        raise ConfigError("Configuration exceeds 64 KiB")
    try:
        raw = tomllib.loads(data.decode("utf-8"))
    except (UnicodeError, tomllib.TOMLDecodeError):
        raise ConfigError("Configuration must be valid UTF-8 TOML") from None
    allowed = {
        "network_timeout",
        "command_timeout",
        "enabled_categories",
        "disabled_checks",
        "verbose",
    }
    if raw.keys() - allowed:
        raise ConfigError("Unknown configuration option (redaction cannot be disabled)")
    for key in ("network_timeout", "command_timeout"):
        v = raw.get(key, 4.0)
        if type(v) not in (int, float) or not math.isfinite(v) or not 0.1 <= v <= 30:
            raise ConfigError("Timeouts must be between 0.1 and 30 seconds")
    for key in ("enabled_categories", "disabled_checks"):
        v = raw.get(key, [])
        if not isinstance(v, list) or any(not isinstance(x, str) for x in v):
            raise ConfigError("Check/category selections must be string arrays")
    if set(raw.get("enabled_categories", CATEGORIES)) - set(CATEGORIES):
        raise ConfigError("Unknown category")
    if type(raw.get("verbose", False)) is not bool:
        raise ConfigError("verbose must be a boolean")
    return Config(
        float(raw.get("network_timeout", 4)),
        float(raw.get("command_timeout", 4)),
        tuple(raw.get("enabled_categories", CATEGORIES)),
        tuple(raw.get("disabled_checks", [])),
        raw.get("verbose", False),
    )


def load_config(path: Path, *, required: bool = False) -> Config:
    try:
        with path.open("rb") as stream:
            return parse_config(stream.read(65537))
    except FileNotFoundError:
        if required:
            raise ConfigError("Requested configuration file does not exist") from None
        return Config()
    except OSError:
        raise ConfigError("Cannot read configuration file") from None
