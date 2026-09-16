"""Compatibility exports and the explicit built-in diagnostic registry."""

from ai_dev_doctor.diagnostics.developer_tools import git_check
from ai_dev_doctor.diagnostics.environment import path_check
from ai_dev_doctor.diagnostics.network import proxy_check
from ai_dev_doctor.diagnostics.registry import registry

__all__ = ["git_check", "path_check", "proxy_check", "registry"]
