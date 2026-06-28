"""Architecture guard for RuntimeContainer facade split."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

_RUNTIME_CONTAINER_PATH = PROJECT_ROOT / "src" / "doge" / "bootstrap" / "runtime.py"

_PUBLIC_RUNTIME_METHODS = [
    "build_event_subscriber",
    "build_runtime_outbox_repository",
    "build_agent_repositories",
    "build_agent_document_repository",
    "build_agent_evidence_repository",
    "build_agent_run_queue",
    "build_agent_idempotency_store",
    "build_agent_unit_of_work",
    "build_create_session_use_case",
    "build_resume_session_use_case",
    "build_list_sessions_use_case",
    "build_append_turn_use_case",
    "build_model_router",
    "build_agent_backends",
    "build_agent_runtime_kernel",
    "build_research_agent_runtime",
    "build_persisted_research_agent_runtime",
    "build_macro_strategist_agent_use_case",
    "build_industry_analyzer_agent_use_case",
    "build_default_tool_registry",
    "build_run_summary_use_case",
    "build_capability_registry_use_case",
    "build_execute_run_use_case",
    "build_resume_run_use_case",
    "gateway_container",
]


def test_runtime_container_does_not_exceed_line_target() -> None:
    source = _RUNTIME_CONTAINER_PATH.read_text(encoding="utf-8")

    assert len(source.splitlines()) <= 100


def test_runtime_container_delegates_to_runtime_factory_modules() -> None:
    source = _RUNTIME_CONTAINER_PATH.read_text(encoding="utf-8")

    assert "from doge.bootstrap.runtime_factories import" in source
    for module_name in ("agent_use_cases", "repositories", "runtime_kernel", "tools", "use_cases"):
        assert f"import {module_name}" in source


def test_runtime_container_has_no_inline_sqlite_construction() -> None:
    source = _RUNTIME_CONTAINER_PATH.read_text(encoding="utf-8")

    forbidden_constructors = [
        "SQLiteApprovalRepository(",
        "SQLiteArtifactRepository(",
        "SQLiteDocumentRepository(",
        "SQLiteEventRepository(",
        "SQLiteEventSubscriber(",
        "SQLiteEvidenceRepository(",
        "SQLiteIdempotencyStore(",
        "SQLiteOutboxRepository(",
        "SQLiteRunQueue(",
        "SQLiteRunRepository(",
        "SQLiteSessionRepository(",
        "SQLiteAgentUnitOfWork(",
    ]
    for constructor in forbidden_constructors:
        assert constructor not in source


def test_runtime_container_retains_public_factory_methods() -> None:
    source = _RUNTIME_CONTAINER_PATH.read_text(encoding="utf-8")

    for method_name in _PUBLIC_RUNTIME_METHODS:
        assert f"def {method_name}" in source, f"RuntimeContainer missing {method_name}"
