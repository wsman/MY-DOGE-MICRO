"""Bootstrap containers should own migrated factory wiring."""

from __future__ import annotations

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


def test_runtime_container_leaf_factories_do_not_delegate_to_composition() -> None:
    for method_name in _RUNTIME_LEAF_FACTORIES:
        source = inspect.getsource(getattr(RuntimeContainer, method_name))

        assert "composition." not in source
        assert "_composition()" not in source


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


def test_workspace_container_factories_do_not_delegate_to_composition() -> None:
    for method_name in _WORKSPACE_FACTORIES:
        source = inspect.getsource(getattr(WorkspaceContainer, method_name))

        assert "composition." not in source
        assert "_composition()" not in source


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
