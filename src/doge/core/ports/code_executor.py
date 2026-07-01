"""Port for bounded code execution adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionResult:
    """Structured result returned by code execution adapters."""

    ok: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    error: str | None = None


class ICodeExecutor(ABC):
    """Executes operator-approved code snippets behind an explicit boundary."""

    @abstractmethod
    def execute(self, code: str, timeout: float) -> ExecutionResult:
        """Execute code and return a bounded, non-throwing result."""


class DisabledCodeExecutor(ICodeExecutor):
    """Fail-closed executor used when Python analysis is not enabled."""

    available = False
    executor_name = "disabled"
    disabled_reason = "Python analysis execution is disabled by configuration."

    def execute(self, code: str, timeout: float) -> ExecutionResult:
        return ExecutionResult(ok=False, error=self.disabled_reason)
