"""Runtime port must carry explicit tenant scope on storage-touching methods."""

from __future__ import annotations

import inspect

import pytest

from doge.core.ports.agent_runtime import IResearchAgentRuntime
from doge.shared.scope import TenantScope


@pytest.mark.parametrize(
    "method_name",
    [
        "queue_run",
        "get_run",
        "list_runs",
        "list_events",
        "list_artifacts",
        "stream_events",
        "resolve_approval",
        "cancel_run",
        "finalize_cancelled",
        "record_failure",
    ],
)
def test_runtime_storage_methods_accept_scope_parameter(method_name: str) -> None:
    signature = inspect.signature(getattr(IResearchAgentRuntime, method_name))
    parameters = list(signature.parameters.values())

    assert parameters[1].name == "scope"


def test_tenant_scope_local_is_explicit_and_enterprise_rejects_blank_tenant() -> None:
    assert TenantScope.local().tenant_id == "local"

    with pytest.raises(ValueError, match="enterprise tenant_id is required"):
        TenantScope.enterprise("")
