"""Architecture guard for runtime factory modules."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
_RUNTIME_FACTORY_ROOT = PROJECT_ROOT / "src" / "doge" / "bootstrap" / "runtime_factories"

_RUNTIME_FACTORY_MODULES = {
    "__init__.py": ["agent_use_cases", "repositories", "runtime_kernel", "tools", "use_cases"],
    "agent_use_cases.py": [
        "build_macro_strategist_agent_use_case",
        "build_industry_analyzer_agent_use_case",
    ],
    "repositories.py": [
        "build_event_subscriber",
        "build_runtime_outbox_repository",
        "build_agent_repositories",
        "build_agent_document_repository",
        "build_agent_evidence_repository",
        "build_agent_run_queue",
        "build_agent_idempotency_store",
        "build_agent_unit_of_work",
        "build_runtime_transaction_factory",
    ],
    "runtime_kernel.py": [
        "build_model_router",
        "build_agent_backends",
        "build_agent_runtime_kernel",
        "build_research_agent_runtime",
        "build_persisted_research_agent_runtime",
    ],
    "tools.py": ["build_default_tool_registry"],
    "use_cases.py": [
        "build_create_session_use_case",
        "build_resume_session_use_case",
        "build_list_sessions_use_case",
        "build_append_turn_use_case",
        "build_run_summary_use_case",
        "build_capability_registry_use_case",
        "build_execute_run_use_case",
        "build_resume_run_use_case",
    ],
}


def test_runtime_factory_modules_export_expected_factories() -> None:
    for file_name, exported_names in _RUNTIME_FACTORY_MODULES.items():
        source = (_RUNTIME_FACTORY_ROOT / file_name).read_text(encoding="utf-8")
        for exported_name in exported_names:
            if file_name == "__init__.py":
                assert f'"{exported_name}"' in source
            else:
                assert f"def {exported_name}" in source, f"{file_name} missing {exported_name}"
