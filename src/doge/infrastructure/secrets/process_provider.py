"""Process-backed secret provider for production secret-store bridges."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from doge.core.ports.secrets import ISecretProvider


_SAFE_SECRET_NAME = re.compile(r"^[A-Za-z0-9_.:-]+$")
_NAME_PLACEHOLDER = "{name}"


@dataclass(frozen=True)
class ProcessSecretProvider(ISecretProvider):
    """Resolve secrets by invoking an operator-controlled command.

    The command is executed without a shell. If any command argument contains
    ``{name}``, that placeholder is replaced with the requested canonical secret
    name; otherwise the name is appended as the final argument.
    """

    command: Sequence[str]
    timeout_seconds: float = 5.0
    allowed_names: frozenset[str] = field(default_factory=frozenset)
    env: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if not self.command:
            raise ValueError("ProcessSecretProvider requires a non-empty command")
        if self.timeout_seconds <= 0:
            raise ValueError("ProcessSecretProvider timeout must be positive")

    def get_secret(self, name: str) -> str | None:
        if not _SAFE_SECRET_NAME.fullmatch(name):
            return None
        if self.allowed_names and name not in self.allowed_names:
            return None

        try:
            result = subprocess.run(
                self._argv(name),
                check=False,
                capture_output=True,
                env=dict(self.env) if self.env is not None else None,
                shell=False,
                text=True,
                timeout=self.timeout_seconds,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            return None

        if result.returncode != 0:
            return None
        value = result.stdout.strip()
        return value or None

    def _argv(self, name: str) -> list[str]:
        argv = [part.replace(_NAME_PLACEHOLDER, name) for part in self.command]
        if not any(_NAME_PLACEHOLDER in part for part in self.command):
            argv.append(name)
        return argv
