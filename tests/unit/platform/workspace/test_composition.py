"""Unit tests for the bc-05 workspace bounded-context composition root (P2B)."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from doge.platform.workspace import composition
from doge.platform.workspace.application import (
    ProjectService,
    ResearchCaseService,
    WorkflowService,
    WorkspaceService,
)


def test_composition_does_not_import_application_composition() -> None:
    """P2B constraint: the workspace composition root stays self-contained.

    AST-based so the check is robust against docstring mentions of the
    forbidden module name.
    """
    source = Path(inspect.getfile(composition)).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("doge.application.composition"), (
                    f"composition root must not import {alias.name}"
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not module.startswith("doge.application.composition"), (
                f"composition root must not import from {module}"
            )
            assert not (
                module == "doge.application"
                and any(alias.name == "composition" for alias in node.names)
            ), "composition root must not import application.composition"


def test_build_workspace_service_binds_injected_dependencies() -> None:
    repo = object()
    governance = object()

    service = composition.build_workspace_service(repo, governance)

    assert isinstance(service, WorkspaceService)
    assert service._repo is repo
    assert service._access._governance is governance


def test_build_project_service_binds_injected_dependencies() -> None:
    repo = object()
    governance = object()

    service = composition.build_project_service(repo, governance)

    assert isinstance(service, ProjectService)
    assert service._repo is repo
    assert service._access._governance is governance


def test_build_workflow_service_binds_injected_dependencies() -> None:
    repo = object()
    governance = object()

    service = composition.build_workflow_service(repo, governance)

    assert isinstance(service, WorkflowService)
    assert service._repo is repo
    assert service._access._governance is governance


def test_build_research_case_service_default_wiring() -> None:
    repo = object()
    governance = object()
    runtime = object()

    service = composition.build_research_case_service(repo, governance, runtime)

    assert isinstance(service, ResearchCaseService)
    assert service._repo is repo
    assert service._access._governance is governance
    assert service._runtime is runtime
    # Default wiring leaves the execution collaborators disabled.
    assert service._documents is None
    assert service._portfolios is None
    assert service._capability_registry is None
    assert service._capability_registry_enabled is False


def test_build_research_case_service_override_wiring() -> None:
    repo = object()
    governance = object()
    runtime = object()
    documents = object()
    portfolios = object()
    capability_registry = object()

    service = composition.build_research_case_service(
        repo,
        governance,
        runtime,
        document_repository=documents,
        portfolio_repository=portfolios,
        capability_registry=capability_registry,
        capability_registry_enabled=True,
    )

    assert isinstance(service, ResearchCaseService)
    assert service._repo is repo
    assert service._access._governance is governance
    assert service._runtime is runtime
    assert service._documents is documents
    assert service._portfolios is portfolios
    assert service._capability_registry is capability_registry
    assert service._capability_registry_enabled is True


def test_build_research_case_service_governance_is_required() -> None:
    """Enterprise governance must always be supplied (tenant fail-closed)."""
    sig = inspect.signature(composition.build_research_case_service)
    # repo / governance / runtime are positional-required (no defaults), so a
    # caller can never construct a research-case service without governance.
    for required_param in ("repo", "governance", "runtime"):
        assert sig.parameters[required_param].default is inspect.Parameter.empty
