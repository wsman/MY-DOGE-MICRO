"""Bootstrap containers should own migrated factory wiring."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import doge.application.composition as composition
from doge.bootstrap.gateway import GatewayContainer
from doge.bootstrap.runtime import RuntimeContainer
from doge.bootstrap.workspace import WorkspaceContainer
from doge.infrastructure.database.agent_repositories import (
    SQLiteDocumentRepository,
    SQLiteEventRepository,
    SQLiteIdempotencyStore,
    SQLiteRunQueue,
)
from doge.infrastructure.database.event_subscriber import SQLiteEventSubscriber
from doge.infrastructure.database.evidence_repository import SQLiteEvidenceRepository
from doge.infrastructure.database.sqlite_runtime_transaction import SQLiteOutboxRepository
from doge.infrastructure.database.sqlite_uow import SQLiteAgentUnitOfWork

PROJECT_ROOT = Path(__file__).resolve().parents[3]


_RUNTIME_LEAF_FACTORIES = [
    "build_agent_repositories",
    "build_runtime_outbox_repository",
    "build_event_subscriber",
    "build_agent_document_repository",
    "build_agent_evidence_repository",
    "build_agent_run_queue",
    "build_agent_idempotency_store",
    "build_agent_unit_of_work",
]

# High-level runtime factories that RuntimeContainer must own directly (P1A).
_RUNTIME_HIGH_LEVEL_FACTORIES = [
    "build_research_agent_runtime",
    "build_persisted_research_agent_runtime",
    "build_run_summary_use_case",
    "build_capability_registry_use_case",
    "build_default_tool_registry",
    "build_execute_run_use_case",
    "build_resume_run_use_case",
]

_WORKSPACE_FACTORIES = [
    "build_portfolio_repository",
    "build_platform_repository",
    "build_enterprise_governance_repository",
    "build_research_case_service",
    "build_workflow_service",
]

_GATEWAY_FACTORIES = [
    "build_secret_provider",
    "build_kimi_agent_model",
    "build_default_text_llm_client",
    "build_report_repository",
    "build_schema_browser",
    "build_stock_repository",
    "build_note_repository",
    "build_stock_name_repository",
    "build_view_repository",
    "build_view_service",
    "build_stock_service",
    "build_ranking_service",
    "build_breadth_service",
    "build_anomaly_service",
    "build_manage_notes_use_case",
    "build_generate_macro_report_use_case",
    "build_rag_service",
    "build_claim_repository",
    "build_generate_industry_report_use_case",
    "build_metadata_source",
    "build_storage_repository",
    "build_tdx_data_source",
    "build_tdx_server_list",
    "build_scan_market_use_case",
    "build_file_upload_service",
]

_APPLICATION_COMPOSITION_IMPORT_ALLOWLIST = {
    "src/ai_analysis/anomaly_detection.py",
    "src/ai_analysis/catalog_generator.py",
    "src/ai_analysis/fetch_names.py",
    "src/ai_analysis/market_overview.py",
    "src/ai_analysis/stock_notes.py",
    "src/doge/core/services/composition.py",
    "src/micro/market_scanner.py",
}


def _imports_application_composition(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == "doge.application.composition" for alias in node.names):
                return True
        if isinstance(node, ast.ImportFrom) and node.module == "doge.application.composition":
            return True
    return False


def test_runtime_container_leaf_factories_do_not_delegate_to_composition() -> None:
    for method_name in _RUNTIME_LEAF_FACTORIES:
        source = inspect.getsource(getattr(RuntimeContainer, method_name))

        assert "composition." not in source
        assert "_composition()" not in source


def test_runtime_module_has_no_composition_helper() -> None:
    """P1A: the ``_composition()`` indirection must be gone from bootstrap.runtime."""
    source = (PROJECT_ROOT / "src" / "doge" / "bootstrap" / "runtime.py").read_text(encoding="utf-8")

    assert "_composition" not in source
    assert "doge.application.composition" not in source


def test_runtime_container_owns_high_level_factories_directly() -> None:
    """P1A: RuntimeContainer owns the high-level runtime factories, not composition."""
    for method_name in _RUNTIME_HIGH_LEVEL_FACTORIES:
        assert hasattr(RuntimeContainer, method_name), f"RuntimeContainer missing {method_name}"
        source = inspect.getsource(getattr(RuntimeContainer, method_name))

        assert "composition." not in source
        assert "_composition()" not in source


def test_composition_high_level_factories_are_runtime_container_shims() -> None:
    """P1A: legacy composition entry points delegate to RuntimeContainer."""
    for factory_name in _RUNTIME_HIGH_LEVEL_FACTORIES:
        assert hasattr(composition, factory_name), f"composition missing {factory_name}"
        source = inspect.getsource(getattr(composition, factory_name))

        assert "_runtime_container" in source


def test_composition_leaf_factories_are_runtime_container_shims() -> None:
    for factory_name in _RUNTIME_LEAF_FACTORIES:
        source = inspect.getsource(getattr(composition, factory_name))

        assert "_runtime_container" in source


def test_runtime_container_leaf_factories_build_expected_adapters(tmp_path) -> None:
    container = RuntimeContainer(db_path=tmp_path / "agent_state.db")
    repos = container.build_agent_repositories()

    assert isinstance(repos["events"], SQLiteEventRepository)
    assert isinstance(repos["documents"], SQLiteDocumentRepository)
    assert isinstance(repos["evidence"], SQLiteEvidenceRepository)
    assert isinstance(container.build_runtime_outbox_repository(), SQLiteOutboxRepository)
    assert isinstance(container.build_event_subscriber(), SQLiteEventSubscriber)
    assert isinstance(container.build_agent_run_queue(), SQLiteRunQueue)
    assert isinstance(container.build_agent_idempotency_store(), SQLiteIdempotencyStore)
    assert isinstance(container.build_agent_unit_of_work(), SQLiteAgentUnitOfWork)


def test_workspace_container_factories_do_not_delegate_to_application_composition() -> None:
    """P2B: WorkspaceContainer may delegate to its own bounded-context
    composition root (doge.platform.workspace.composition) but must not
    delegate to the legacy application mega-composition."""
    for method_name in _WORKSPACE_FACTORIES:
        source = inspect.getsource(getattr(WorkspaceContainer, method_name))

        assert "application.composition" not in source
        assert "_composition()" not in source


def test_workspace_container_delegates_service_factories_to_composition_root() -> None:
    """P2B: research-case + workflow service construction delegates to the
    bounded-context composition root instead of being constructed inline."""
    for method_name in ("build_research_case_service", "build_workflow_service"):
        source = inspect.getsource(getattr(WorkspaceContainer, method_name))

        assert "composition.build_" in source, (
            f"{method_name} must delegate to doge.platform.workspace.composition"
        )


def test_gateway_container_factories_do_not_delegate_to_composition() -> None:
    for method_name in _GATEWAY_FACTORIES:
        source = inspect.getsource(getattr(GatewayContainer, method_name))

        assert "composition." not in source
        assert "_composition()" not in source


def test_composition_leaf_factories_are_gateway_container_shims() -> None:
    for factory_name in _GATEWAY_FACTORIES:
        source = inspect.getsource(getattr(composition, factory_name))

        assert "_gateway_container" in source


def test_migrated_entrypoints_use_bootstrap_not_legacy_composition() -> None:
    paths = [
        "src/doge/interfaces/api/routers/v1/tools.py",
        "src/doge/interfaces/api/routers/scan.py",
        "src/doge/interfaces/cli/commands/anomaly.py",
        "src/doge/interfaces/cli/commands/breadth.py",
        "src/doge/interfaces/cli/commands/case.py",
        "src/doge/interfaces/cli/commands/demo.py",
        "src/doge/interfaces/cli/commands/macro.py",
        "src/doge/interfaces/cli/commands/run.py",
        "src/doge/interfaces/cli/commands/rsrs.py",
        "src/doge/interfaces/cli/commands/session.py",
        "src/doge/interfaces/cli/commands/stock.py",
        "src/doge/interfaces/cli/commands/template.py",
        "src/doge/interfaces/mcp/server.py",
        "src/doge/interfaces/mcp/tools/anomaly.py",
        "src/doge/interfaces/mcp/tools/query_stock.py",
        "src/doge/interfaces/mcp/tools/ranking.py",
        "src/doge/interfaces/mcp/tools/views.py",
    ]
    for relative_path in paths:
        source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

        assert "doge.application.composition" not in source
        assert "from doge.application import composition" not in source


def test_application_package_does_not_eagerly_import_composition() -> None:
    source = (PROJECT_ROOT / "src/doge/application/__init__.py").read_text(encoding="utf-8")

    assert "from doge.application.composition import" not in source


def test_application_composition_imports_are_legacy_allowlisted() -> None:
    """G7B: new src code must use bootstrap/process roots, not the legacy shim."""
    offenders = []
    for path in sorted((PROJECT_ROOT / "src").rglob("*.py")):
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        if relative in _APPLICATION_COMPOSITION_IMPORT_ALLOWLIST:
            continue
        if _imports_application_composition(path):
            offenders.append(relative)

    assert offenders == []


def test_application_composition_allowlist_documents_current_legacy_users() -> None:
    missing = [
        relative
        for relative in sorted(_APPLICATION_COMPOSITION_IMPORT_ALLOWLIST)
        if not _imports_application_composition(PROJECT_ROOT / relative)
    ]

    assert missing == []
