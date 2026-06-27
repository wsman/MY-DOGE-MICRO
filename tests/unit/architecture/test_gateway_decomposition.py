"""Architecture guard for GatewayContainer decomposition."""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]

_GATEWAY_CONTAINER_PATH = PROJECT_ROOT / "src" / "doge" / "bootstrap" / "gateway.py"


def test_gateway_container_does_not_exceed_line_target() -> None:
    source = _GATEWAY_CONTAINER_PATH.read_text(encoding="utf-8")
    lines = source.splitlines()
    assert len(lines) <= 150, f"GatewayContainer has {len(lines)} lines"


def test_gateway_container_delegates_factories_to_bounded_context_modules() -> None:
    source = _GATEWAY_CONTAINER_PATH.read_text(encoding="utf-8")
    # Verify all seven factory modules are imported
    assert "from doge.bootstrap.gateway_factories import" in source
    factory_modules = [
        "documents",
        "llm",
        "market",
        "repositories",
        "secrets",
        "tools",
        "use_cases",
    ]
    for module in factory_modules:
        assert f"import {module}" in source or f"import {module}\n" in source, f"GatewayContainer must delegate to {module}"
    # Verify no inline adapter construction remains (all delegation)
    assert "DuckDBMarketViewRepository(" not in source
    assert "SQLiteReportRepository(" not in source
    assert "KimiAgentModel(" not in source
    assert "EnvSecretProvider(" not in source


def test_gateway_container_retains_public_factory_methods() -> None:
    """The public facade surface must remain stable for compatibility."""
    source = _GATEWAY_CONTAINER_PATH.read_text(encoding="utf-8")
    required_methods = [
        "def build_secret_provider",
        "def build_kimi_agent_model",
        "def build_default_text_llm_client",
        "def build_view_service",
        "def build_stock_service",
        "def build_ranking_service",
        "def build_breadth_service",
        "def build_anomaly_service",
        "def build_rag_service",
        "def build_file_upload_service",
        "def build_tool_application_service",
        "def build_python_analysis_executor",
        "def runtime_container",
        "def workspace_container",
    ]
    for method in required_methods:
        assert method in source, f"GatewayContainer missing public method: {method}"
