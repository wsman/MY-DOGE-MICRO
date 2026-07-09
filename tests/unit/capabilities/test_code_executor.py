from doge.application.agent.tool_service import ToolApplicationService
import subprocess

import pytest
from doge.infrastructure.code_execution.python import DisabledCodeExecutor, SubprocessCodeExecutor
from doge.products.quant.tools import QuantToolProvider
from doge.bootstrap.gateway import GatewayContainer
def build_python_analysis_executor(*a, **kw): return GatewayContainer().build_python_analysis_executor(*a, **kw)
from doge.config.settings import FeatureConfig, Settings
from doge.core.ports.code_executor import ICodeExecutor
from doge.infrastructure.code_execution import (
    DisabledCodeExecutor as InfrastructureDisabledCodeExecutor,
)
from doge.infrastructure.code_execution import (
    SubprocessCodeExecutor as InfrastructureSubprocessCodeExecutor,
)

pytestmark = pytest.mark.module_quant


def test_disabled_code_executor_is_default_off_boundary():
    result = DisabledCodeExecutor().execute("print('ok')", timeout=1.0)

    assert result.ok is False
    assert result.error == "Python analysis execution is disabled by configuration."


def test_quant_provider_uses_injected_disabled_executor_by_default():
    result = QuantToolProvider().run_python_analysis("print('ok')")

    assert result == {
        "ok": False,
        "stdout": "",
        "stderr": "",
        "returncode": None,
        "error": "Python analysis execution is disabled by configuration.",
    }


def test_subprocess_code_executor_preserves_demo_execution_when_explicitly_selected():
    result = SubprocessCodeExecutor().execute("print('ok')", timeout=1.0)

    assert result.ok is True
    assert result.stdout.strip() == "ok"
    assert result.stderr == ""
    assert result.returncode == 0


def test_subprocess_code_executor_keeps_legacy_unsafe_code_guard():
    result = SubprocessCodeExecutor().execute("import os\nprint(os.getcwd())", timeout=1.0)

    assert result.ok is False
    assert result.error == "Code uses disallowed operations in the demo sandbox."


@pytest.mark.parametrize(
    "code",
    [
        "import os\nprint(os.getcwd())",
        "import socket\nprint(socket.socket())",
        "import sqlite3\nprint(sqlite3.connect(':memory:'))",
        "import subprocess\nprint(subprocess.run(['echo', 'x']))",
    ],
)
def test_subprocess_code_executor_denies_direct_escape_imports(code):
    result = SubprocessCodeExecutor().execute(code, timeout=1.0)

    assert result.ok is False
    assert result.error == "Code uses disallowed operations in the demo sandbox."


def test_subprocess_code_executor_scrubs_secret_environment(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-value")
    monkeypatch.setenv("DOGE_SLOT_TRUSTED_PUBLISHER_KEYS", "ops=secret")
    code = (
        "import importlib\n"
        "os_mod = importlib.import_module('os')\n"
        "print(os_mod.environ.get('DEEPSEEK_API_KEY'))\n"
        "print(os_mod.environ.get('DOGE_SLOT_TRUSTED_PUBLISHER_KEYS'))\n"
    )

    result = SubprocessCodeExecutor().execute(code, timeout=1.0)

    assert result.ok is True
    assert result.stdout.splitlines() == ["None", "None"]


def test_subprocess_code_executor_runs_from_scratch_cwd():
    code = (
        "import importlib\n"
        "os_mod = importlib.import_module('os')\n"
        "print(os_mod.getcwd())\n"
    )

    result = SubprocessCodeExecutor().execute(code, timeout=1.0)

    assert result.ok is True
    assert "doge-python-analysis-" in result.stdout
    assert str(result.stdout).strip() != str(__import__("os").getcwd())


def test_composition_requires_feature_flag_before_subprocess_executor():
    disabled = build_python_analysis_executor(
        Settings(features=FeatureConfig(python_analysis_enabled=False, python_analysis_executor="subprocess"))
    )
    enabled = build_python_analysis_executor(
        Settings(features=FeatureConfig(python_analysis_enabled=True, python_analysis_executor="subprocess"))
    )

    assert isinstance(disabled, DisabledCodeExecutor)
    assert isinstance(enabled, SubprocessCodeExecutor)
    assert enabled.isolation_enabled is False


def test_composition_enables_code_string_isolation_only_when_both_flags_are_on():
    disabled = build_python_analysis_executor(
        Settings(
            features=FeatureConfig(
                python_analysis_enabled=False,
                python_analysis_executor="subprocess",
                slot_code_string_isolation=True,
            )
        )
    )
    enabled = build_python_analysis_executor(
        Settings(
            features=FeatureConfig(
                python_analysis_enabled=True,
                python_analysis_executor="subprocess",
                slot_code_string_isolation=True,
            )
        )
    )

    assert isinstance(disabled, DisabledCodeExecutor)
    assert isinstance(enabled, SubprocessCodeExecutor)
    assert enabled.isolation_enabled is True


def test_tool_application_service_reports_executor_capability_status():
    disabled = ToolApplicationService().python_analysis_capability_status()
    enabled = ToolApplicationService(code_executor=SubprocessCodeExecutor()).python_analysis_capability_status()

    assert disabled["status"] == "disabled"
    assert disabled["metadata"]["executor"] == "disabled"
    assert enabled == {"status": "available", "metadata": {"executor": "subprocess"}}


def test_tool_application_service_reports_code_string_isolation_scope():
    enabled = ToolApplicationService(
        code_executor=SubprocessCodeExecutor(isolation_enabled=True)
    ).python_analysis_capability_status()

    assert enabled["status"] == (
        "available"
        if enabled["metadata"]["isolation_mode"] == "windows_job_object"
        else "disabled"
    )
    assert enabled["metadata"]["isolation_scope"] == "code_string_only"
    assert enabled["metadata"]["isolation_mode"] in {
        "windows_job_object",
        "unavailable_non_windows",
    }


def test_tool_application_service_marks_unavailable_isolation_host_disabled(monkeypatch):
    import doge.infrastructure.code_execution.python as python_executor

    monkeypatch.setattr(python_executor.os, "name", "posix")

    status = ToolApplicationService(
        code_executor=SubprocessCodeExecutor(isolation_enabled=True)
    ).python_analysis_capability_status()

    assert status["status"] == "disabled"
    assert status["metadata"]["executor"] == "subprocess_isolation_unavailable"
    assert status["metadata"]["isolation_mode"] == "unavailable_non_windows"
    assert status["metadata"]["isolation_scope"] == "code_string_only"


def test_job_object_resource_limit_failure_is_fail_closed_and_audited(monkeypatch, tmp_path):
    import doge.infrastructure.code_execution.python as python_executor

    events = []

    class FakeJob:
        def __init__(self, limits):
            self.limits = limits
            self.closed = False

        def assign(self, process):
            process.assigned = True

        def terminate(self, *, exit_code):
            self.terminated = exit_code

        def close(self):
            self.closed = True

    class FakeProcess:
        args = ["py", "-c"]
        assigned = False

        def __init__(self):
            self.returncode = python_executor._WINDOWS_STATUS_QUOTA_EXCEEDED - (1 << 32)

        def communicate(self, timeout=None):
            return "before-limit", ""

        def kill(self):
            self.killed = True

    monkeypatch.setattr(python_executor, "_WindowsJobObject", FakeJob)
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: FakeProcess())

    executor = SubprocessCodeExecutor(isolation_enabled=True, audit_sink=events.append)
    result = executor._execute_with_windows_job_object("print('ok')", 1.0, str(tmp_path))

    assert result.ok is False
    assert result.error == "Python analysis exceeded resource limits."
    assert result.stdout == "before-limit"
    assert events[0]["event_type"] == "slot_resource_limit_exceeded"
    assert events[0]["resource_type"] == "code_string"


def test_job_object_plain_nonzero_exit_is_not_reported_as_resource_limit(monkeypatch, tmp_path):
    import doge.infrastructure.code_execution.python as python_executor

    events = []

    class FakeJob:
        def __init__(self, limits):
            self.limits = limits

        def assign(self, process):
            process.assigned = True

        def terminate(self, *, exit_code):
            self.terminated = exit_code

        def close(self):
            self.closed = True

    class FakeProcess:
        args = ["py", "-c"]
        returncode = 1
        assigned = False

        def communicate(self, timeout=None):
            return "", ""

        def kill(self):
            self.killed = True

    monkeypatch.setattr(python_executor, "_WindowsJobObject", FakeJob)
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: FakeProcess())

    executor = SubprocessCodeExecutor(isolation_enabled=True, audit_sink=events.append)
    result = executor._execute_with_windows_job_object("raise SystemExit(1)", 1.0, str(tmp_path))

    assert result.ok is False
    assert result.returncode == 1
    assert result.error is None
    assert events == []


def test_infrastructure_code_executors_implement_port():
    assert isinstance(InfrastructureDisabledCodeExecutor(), ICodeExecutor)
    assert isinstance(InfrastructureSubprocessCodeExecutor(), ICodeExecutor)
