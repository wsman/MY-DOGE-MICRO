from __future__ import annotations

import inspect

from doge.core.ports.runtime_services import (
    IApprovalCoordinator,
    IRunLifecycleService,
    IRunStepper,
)


def test_runtime_stepper_protocol_is_scope_first() -> None:
    parameters = list(inspect.signature(IRunStepper.step).parameters.values())

    assert [parameter.name for parameter in parameters[:3]] == ["self", "scope", "run_id"]
    assert "tenant_id" not in inspect.signature(IRunStepper.step).parameters


def test_runtime_approval_protocol_is_scope_first() -> None:
    parameters = list(inspect.signature(IApprovalCoordinator.resolve).parameters.values())

    assert [parameter.name for parameter in parameters[:5]] == [
        "self",
        "scope",
        "run_id",
        "approval_id",
        "approved",
    ]
    assert "tenant_id" not in inspect.signature(IApprovalCoordinator.resolve).parameters


def test_runtime_lifecycle_protocols_are_scope_first() -> None:
    expected = {
        "create_run": ["self", "scope", "request"],
        "run_to_pause_or_completion": ["self", "scope", "run_id"],
        "queue_run": ["self", "scope", "run_id", "reason"],
        "cancel_run": ["self", "scope", "run_id"],
        "finalize_cancelled": ["self", "scope", "run_id"],
        "record_failure": ["self", "scope", "run_id", "message"],
        "get_run": ["self", "scope", "run_id"],
        "list_events": ["self", "scope", "run_id"],
        "list_runs": ["self", "scope", "session_id", "limit"],
        "list_artifacts": ["self", "scope", "run_id"],
    }

    for method_name, parameter_names in expected.items():
        signature = inspect.signature(getattr(IRunLifecycleService, method_name))
        assert list(signature.parameters)[: len(parameter_names)] == parameter_names
        assert "tenant_id" not in signature.parameters
