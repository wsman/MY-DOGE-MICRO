"""Python analysis executor adapters."""

from __future__ import annotations

import subprocess
import sys

from doge.application.capabilities.tool_utils import unsafe_python
from doge.core.ports.code_executor import ExecutionResult, ICodeExecutor


class DisabledCodeExecutor(ICodeExecutor):
    """Fail-closed executor used when Python analysis is not enabled."""

    available = False
    executor_name = "disabled"
    disabled_reason = "Python analysis execution is disabled by configuration."

    def execute(self, code: str, timeout: float) -> ExecutionResult:
        return ExecutionResult(ok=False, error=self.disabled_reason)


class SubprocessCodeExecutor(ICodeExecutor):
    """Demo Python executor preserving the legacy local subprocess behavior."""

    available = True
    executor_name = "subprocess"

    def execute(self, code: str, timeout: float) -> ExecutionResult:
        if unsafe_python(code):
            return ExecutionResult(ok=False, error="Code uses disallowed operations in the demo sandbox.")
        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-c", code],
                text=True,
                capture_output=True,
                timeout=max(1.0, min(float(timeout), 10.0)),
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(ok=False, error="Python analysis timed out.")
        return ExecutionResult(
            ok=completed.returncode == 0,
            stdout=completed.stdout[-4000:],
            stderr=completed.stderr[-2000:] if completed.returncode else "",
            returncode=completed.returncode,
        )
