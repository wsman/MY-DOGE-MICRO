from doge.application.agent.tool_service import ToolApplicationService
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


def test_tool_application_service_reports_executor_capability_status():
    disabled = ToolApplicationService().python_analysis_capability_status()
    enabled = ToolApplicationService(code_executor=SubprocessCodeExecutor()).python_analysis_capability_status()

    assert disabled["status"] == "disabled"
    assert disabled["metadata"]["executor"] == "disabled"
    assert enabled == {"status": "available", "metadata": {"executor": "subprocess"}}


def test_infrastructure_code_executors_implement_port():
    assert isinstance(InfrastructureDisabledCodeExecutor(), ICodeExecutor)
    assert isinstance(InfrastructureSubprocessCodeExecutor(), ICodeExecutor)
