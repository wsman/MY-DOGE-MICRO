"""Infrastructure implementations for Python code execution."""

from __future__ import annotations

import ctypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Any, Callable

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


CodeExecutionAuditSink = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class CodeExecutionResourceLimits:
    """Resource limits for the default-off code-string isolation prototype."""

    process_memory_bytes: int = 256 * 1024 * 1024
    job_memory_bytes: int = 512 * 1024 * 1024
    cpu_seconds: float = 5.0


class SubprocessCodeExecutor(ICodeExecutor):
    """Demo Python executor with explicit env/cwd hardening.

    By default this remains the P4 local subprocess boundary: scrubbed env,
    scratch cwd, and bounded wall-clock timeout. When ``isolation_enabled`` is
    explicitly set on Windows, the child is additionally assigned to a Job
    Object with process/job memory and per-process user-time limits. That is a
    code-string resource-isolation prototype, not provider-code containment.
    """

    def __init__(
        self,
        *,
        isolation_enabled: bool = False,
        resource_limits: CodeExecutionResourceLimits | None = None,
        audit_sink: CodeExecutionAuditSink | None = None,
    ) -> None:
        self.isolation_enabled = isolation_enabled
        self.resource_limits = resource_limits or CodeExecutionResourceLimits()
        self._audit_sink = audit_sink

    @property
    def available(self) -> bool:
        return not self.isolation_enabled or os.name == "nt"

    @property
    def executor_name(self) -> str:
        if not self.isolation_enabled:
            return "subprocess"
        if os.name == "nt":
            return "subprocess_job_object"
        return "subprocess_isolation_unavailable"

    @property
    def isolation_mode(self) -> str:
        if not self.isolation_enabled:
            return "subprocess_soft"
        if os.name == "nt":
            return "windows_job_object"
        return "unavailable_non_windows"

    def execute(self, code: str, timeout: float) -> ExecutionResult:
        if _unsafe_python(code):
            return ExecutionResult(ok=False, error="Code uses disallowed operations in the demo sandbox.")
        scratch = tempfile.mkdtemp(prefix="doge-python-analysis-")
        bounded_timeout = _bounded_timeout(timeout)
        try:
            if self.isolation_enabled and os.name == "nt":
                return self._execute_with_windows_job_object(code, bounded_timeout, scratch)
            if self.isolation_enabled:
                return ExecutionResult(
                    ok=False,
                    error="Python analysis code-string isolation is only available on Windows Job Objects in this prototype.",
                )
            completed = subprocess.run(
                [sys.executable, "-I", "-c", code],
                text=True,
                capture_output=True,
                timeout=bounded_timeout,
                check=False,
                cwd=scratch,
                env=_sanitized_env(os.environ),
                start_new_session=(os.name != "nt"),
                creationflags=_windows_creation_flags(),
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(ok=False, error="Python analysis timed out.")
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
        return _completed_process_result(completed)

    def _execute_with_windows_job_object(
        self,
        code: str,
        timeout: float,
        scratch: str,
    ) -> ExecutionResult:
        try:
            job = _WindowsJobObject(self.resource_limits)
        except OSError as exc:
            return ExecutionResult(
                ok=False,
                error=f"Python analysis isolation could not be established: {exc}",
            )
        try:
            process = subprocess.Popen(
                [sys.executable, "-I", "-c", code],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=scratch,
                env=_sanitized_env(os.environ),
                creationflags=_windows_creation_flags(),
            )
            try:
                job.assign(process)
            except OSError as exc:
                job.terminate(exit_code=1)
                process.kill()
                process.communicate()
                return ExecutionResult(
                    ok=False,
                    error=f"Python analysis isolation could not be established: {exc}",
                )
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                job.terminate(exit_code=1)
                process.kill()
                process.communicate()
                return ExecutionResult(ok=False, error="Python analysis timed out.")
            completed = subprocess.CompletedProcess(
                process.args,
                process.returncode,
                stdout=stdout,
                stderr=stderr,
            )
            if _completed_process_indicates_resource_limit(completed):
                self._audit_resource_limit(completed)
                return _resource_limited_result(completed)
            return _completed_process_result(completed)
        finally:
            job.close()

    def _audit_resource_limit(self, completed: subprocess.CompletedProcess[str]) -> None:
        if self._audit_sink is None:
            return
        try:
            self._audit_sink(
                {
                    "event_type": "slot_resource_limit_exceeded",
                    "resource_type": "code_string",
                    "resource_id": "run_python_analysis",
                    "executor": self.executor_name,
                    "isolation_mode": self.isolation_mode,
                    "returncode": completed.returncode,
                    "limits": {
                        "process_memory_bytes": self.resource_limits.process_memory_bytes,
                        "job_memory_bytes": self.resource_limits.job_memory_bytes,
                        "cpu_seconds": self.resource_limits.cpu_seconds,
                    },
                }
            )
        except Exception:
            pass


def _completed_process_result(completed: subprocess.CompletedProcess[str]) -> ExecutionResult:
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    return ExecutionResult(
        ok=completed.returncode == 0,
        stdout=stdout[-4000:],
        stderr=stderr[-2000:] if completed.returncode else "",
        returncode=completed.returncode,
    )


def _resource_limited_result(completed: subprocess.CompletedProcess[str]) -> ExecutionResult:
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    return ExecutionResult(
        ok=False,
        stdout=stdout[-4000:],
        stderr=stderr[-2000:],
        returncode=completed.returncode,
        error="Python analysis exceeded resource limits.",
    )


def _completed_process_indicates_resource_limit(completed: subprocess.CompletedProcess[str]) -> bool:
    if completed.returncode == 0:
        return False
    stderr = (completed.stderr or "").strip().lower()
    if "memoryerror" in stderr:
        return True
    return _normalized_windows_returncode(completed.returncode) in _WINDOWS_JOB_OBJECT_LIMIT_RETURN_CODES


def _normalized_windows_returncode(returncode: int | None) -> int | None:
    if returncode is None:
        return None
    return int(returncode) & 0xFFFFFFFF


def _bounded_timeout(timeout: float) -> float:
    return max(1.0, min(float(timeout), 10.0))


def _windows_creation_flags() -> int:
    if os.name == "nt" and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        return subprocess.CREATE_NEW_PROCESS_GROUP
    return 0


def _unsafe_python(code: str) -> bool:
    lowered = code.lower()
    blocked = (
        "import os",
        "import sqlite3",
        "import subprocess",
        "import socket",
        "from os",
        "from sqlite3",
        "from subprocess",
        "from socket",
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


class _WindowsJobObject:
    """Small ctypes wrapper for Windows Job Object resource limits."""

    def __init__(self, limits: CodeExecutionResourceLimits) -> None:
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._configure_prototypes()
        self._handle = self._kernel32.CreateJobObjectW(None, None)
        if not self._handle:
            _raise_last_win_error("CreateJobObjectW")
        try:
            self._set_limits(limits)
        except Exception:
            self.close()
            raise

    def assign(self, process: subprocess.Popen[str]) -> None:
        process_handle = getattr(process, "_handle", None)
        if process_handle is None:
            raise OSError("subprocess handle is not available for Job Object assignment")
        if not self._kernel32.AssignProcessToJobObject(self._handle, process_handle):
            _raise_last_win_error("AssignProcessToJobObject")

    def terminate(self, *, exit_code: int) -> None:
        if self._handle:
            self._kernel32.TerminateJobObject(self._handle, exit_code)

    def close(self) -> None:
        if self._handle:
            self._kernel32.CloseHandle(self._handle)
            self._handle = None

    def _configure_prototypes(self) -> None:
        self._kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, ctypes.c_wchar_p)
        self._kernel32.CreateJobObjectW.restype = ctypes.c_void_p
        self._kernel32.SetInformationJobObject.argtypes = (
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_ulong,
        )
        self._kernel32.SetInformationJobObject.restype = ctypes.c_int
        self._kernel32.AssignProcessToJobObject.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
        self._kernel32.AssignProcessToJobObject.restype = ctypes.c_int
        self._kernel32.TerminateJobObject.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        self._kernel32.TerminateJobObject.restype = ctypes.c_int
        self._kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        self._kernel32.CloseHandle.restype = ctypes.c_int

    def _set_limits(self, limits: CodeExecutionResourceLimits) -> None:
        info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        flags = (
            _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            | _JOB_OBJECT_LIMIT_PROCESS_MEMORY
            | _JOB_OBJECT_LIMIT_JOB_MEMORY
        )
        cpu_ticks = max(0, int(float(limits.cpu_seconds) * 10_000_000))
        if cpu_ticks:
            flags |= _JOB_OBJECT_LIMIT_PROCESS_TIME
            info.BasicLimitInformation.PerProcessUserTimeLimit = cpu_ticks
        info.BasicLimitInformation.LimitFlags = flags
        info.ProcessMemoryLimit = max(1, int(limits.process_memory_bytes))
        info.JobMemoryLimit = max(1, int(limits.job_memory_bytes))
        if not self._kernel32.SetInformationJobObject(
            self._handle,
            _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
            ctypes.byref(info),
            ctypes.sizeof(info),
        ):
            _raise_last_win_error("SetInformationJobObject")


class _IO_COUNTERS(ctypes.Structure):
    _fields_ = (
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    )


class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = (
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", ctypes.c_ulong),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_ulong),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_ulong),
        ("SchedulingClass", ctypes.c_ulong),
    )


class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = (
        ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    )


_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9
_JOB_OBJECT_LIMIT_PROCESS_TIME = 0x00000002
_JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
_JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_WINDOWS_STATUS_CONTROL_C_EXIT = 0xC000013A
_WINDOWS_STATUS_QUOTA_EXCEEDED = 0xC0000044
_WINDOWS_STATUS_COMMITMENT_LIMIT = 0xC000012D
_WINDOWS_JOB_OBJECT_LIMIT_RETURN_CODES = {
    _WINDOWS_STATUS_CONTROL_C_EXIT,
    _WINDOWS_STATUS_QUOTA_EXCEEDED,
    _WINDOWS_STATUS_COMMITMENT_LIMIT,
}


def _raise_last_win_error(api_name: str) -> None:
    error = ctypes.get_last_error()
    message = ctypes.FormatError(error).strip()
    raise OSError(error, f"{api_name} failed: {message}")
