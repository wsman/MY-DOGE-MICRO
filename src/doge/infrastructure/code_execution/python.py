"""Infrastructure implementations for Python code execution."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile

from doge.core.ports.code_executor import DisabledCodeExecutor, ExecutionResult, ICodeExecutor

_SECRET_ENV_NAMES = frozenset(
    {
        "MOONSHOT_API_KEY",
        "KIMI_API_KEY",
        "DEEPSEEK_API_KEY",
        "DOGE_AUTH_STATIC_BEARER_TOKEN",
        "DOGE_SECRET_ALLOWED_NAMES",
        "DOGE_SECRET_PROCESS_COMMAND",
        "DOGE_SECRET_PROCESS_TIMEOUT_SECONDS",
        "DOGE_SLOT_TRUSTED_PUBLISHER_KEYS",
    }
)
_SECRET_ENV_RE = re.compile(r"(^|_)(API_KEY|SECRET|TOKEN)(_|$)|API_KEY$", re.IGNORECASE)
_SAFE_ENV_NAMES = frozenset(
    {
        "COMSPEC",
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "PATHEXT",
        "PYTHONIOENCODING",
        "SystemRoot",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "USERPROFILE",
        "WINDIR",
    }
)


class SubprocessCodeExecutor(ICodeExecutor):
    """Demo Python executor with explicit env/cwd hardening.

    This remains a local subprocess boundary, not an OS sandbox. Windows in
    particular has no rlimit/seccomp/chroot equivalent here.
    """

    available = True
    executor_name = "subprocess"

    def execute(self, code: str, timeout: float) -> ExecutionResult:
        if _unsafe_python(code):
            return ExecutionResult(ok=False, error="Code uses disallowed operations in the demo sandbox.")
        scratch = tempfile.mkdtemp(prefix="doge-python-analysis-")
        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-c", code],
                text=True,
                capture_output=True,
                timeout=max(1.0, min(float(timeout), 10.0)),
                check=False,
                cwd=scratch,
                env=_sanitized_env(os.environ),
                start_new_session=(os.name != "nt"),
                creationflags=(
                    subprocess.CREATE_NEW_PROCESS_GROUP
                    if os.name == "nt" and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP")
                    else 0
                ),
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(ok=False, error="Python analysis timed out.")
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
        return ExecutionResult(
            ok=completed.returncode == 0,
            stdout=completed.stdout[-4000:],
            stderr=completed.stderr[-2000:] if completed.returncode else "",
            returncode=completed.returncode,
        )


def _unsafe_python(code: str) -> bool:
    lowered = code.lower()
    blocked = (
        "import os",
        "import subprocess",
        "import socket",
        "from os",
        "from subprocess",
        "open(",
        "__",
        "eval(",
        "exec(",
    )
    return any(token in lowered for token in blocked)


def _sanitized_env(environ: os._Environ[str] | dict[str, str]) -> dict[str, str]:
    """Return a minimal child-process environment without secret-bearing vars."""

    clean: dict[str, str] = {}
    for name, value in environ.items():
        if name in _SECRET_ENV_NAMES or _SECRET_ENV_RE.search(name):
            continue
        if name in _SAFE_ENV_NAMES:
            clean[name] = value
    return clean
