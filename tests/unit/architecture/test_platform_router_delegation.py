"""Architecture guard for platform router service delegation (P1D)."""

from pathlib import Path

ROUTER_DIR = Path("src/doge/interfaces/api/routers/v1")

# platform.py is now a thin aggregator; the focused sub-routers and the shared
# _platform_common module hold the routes, models, service factories, and helpers.
PLATFORM_ROUTER_FILES = [
    ROUTER_DIR / "platform.py",
    ROUTER_DIR / "_platform_common.py",
    ROUTER_DIR / "capabilities.py",
    ROUTER_DIR / "workspaces.py",
    ROUTER_DIR / "projects.py",
    ROUTER_DIR / "cases.py",
    ROUTER_DIR / "case_runs.py",
    ROUTER_DIR / "workflows.py",
]

# Router-level repo orchestration must never leak into the API layer. These
# tokens name repo/orm-level operations that belong in services, not routers.
FORBIDDEN_IN_ANY_PLATFORM_ROUTER = [
    "repo.",
    "save_workspace",
    "save_project",
    "save_case",
    "link_case_run",
    "link_workflow_template_run",
    "build_template_run_request",
    "TemplateRunInput",
    "ensure_resource_access",
    "grant_creator_access",
    "filter_accessible_resource_ids",
]


def test_platform_routers_do_not_orchestrate_repos_directly() -> None:
    for path in PLATFORM_ROUTER_FILES:
        source = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_IN_ANY_PLATFORM_ROUTER:
            assert token not in source, f"{path} contains forbidden token: {token}"


def test_platform_aggregator_is_thin() -> None:
    """P1D: platform.py only includes the focused sub-routers."""
    source = (ROUTER_DIR / "platform.py").read_text(encoding="utf-8")

    assert "include_router" in source
    # No direct route handlers or service orchestration in the aggregator.
    assert "@router." not in source
    for service_name in [
        "WorkspaceService",
        "ProjectService",
        "ResearchCaseService",
        "WorkflowService",
    ]:
        assert service_name not in source, (
            f"platform.py aggregator must not reference {service_name} directly"
        )


def test_platform_routers_delegate_service_construction_to_composition_root() -> None:
    """P2C: _platform_common factories delegate to the workspace composition
    root; no inline service construction remains in the router layer."""
    common = (ROUTER_DIR / "_platform_common.py").read_text(encoding="utf-8")
    composition_src = Path("src/doge/platform/workspace/composition.py").read_text(encoding="utf-8")

    # Each workspace service factory delegates through the composition root.
    for builder in (
        "composition.build_workspace_service",
        "composition.build_project_service",
        "composition.build_research_case_service",
        "composition.build_workflow_service",
    ):
        assert builder in common, f"_platform_common must delegate via {builder}"

    # No inline service construction remains in the router common module.
    for construction in (
        "WorkspaceService(",
        "ProjectService(",
        "ResearchCaseService(",
        "WorkflowService(",
    ):
        assert construction not in common, f"_platform_common must not construct {construction}"

    # The service classes are constructed in the bounded-context composition root.
    for service_name in (
        "WorkspaceService",
        "ProjectService",
        "ResearchCaseService",
        "WorkflowService",
    ):
        assert service_name in composition_src, (
            f"composition root missing service construction: {service_name}"
        )


def test_platform_subrouters_are_self_contained() -> None:
    """P1D: every focused sub-router defines its own routes."""
    subrouters = {
        "capabilities.py": "/capabilities",
        "workspaces.py": "/workspaces",
        "projects.py": "/projects",
        "cases.py": "/research-cases",
        "case_runs.py": "/research-cases/{case_id}/runs",
        "workflows.py": "/workflow-templates",
    }
    for filename, route_prefix in subrouters.items():
        source = (ROUTER_DIR / filename).read_text(encoding="utf-8")
        assert "router = APIRouter" in source, f"{filename} must define its own router"
        assert route_prefix in source, f"{filename} must define routes under {route_prefix}"


def test_gate5_priority_routers_delegate_behavior_to_handlers() -> None:
    """G5C: priority v1 routers stay thin after handler extraction."""

    priority_files = [
        "sessions.py",
        "run_actions.py",
        "run_queries.py",
        "run_stream.py",
        "case_runs.py",
        "cases.py",
        "workflows.py",
        "workspaces.py",
        "projects.py",
    ]
    forbidden_tokens = [
        "service.",
        "worker.",
        ".execute(",
        "authorized_run",
        "build_authorized_summary",
        "redact_run_summary_for_request",
        "ensure_resource_access",
        "trusted_identity_snapshot",
        "trusted_model_policy",
        "append_audit",
    ]

    for filename in priority_files:
        source = (ROUTER_DIR / filename).read_text(encoding="utf-8")
        for token in forbidden_tokens:
            assert token not in source, f"{filename} contains router behavior token: {token}"
