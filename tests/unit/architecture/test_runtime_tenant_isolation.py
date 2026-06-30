"""Runtime port must carry explicit tenant scope on storage-touching methods."""

from __future__ import annotations

import inspect
from pathlib import Path

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
        "resume_run",
        "resolve_approval",
        "resolve_approval_and_resume",
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


def test_core_ports_do_not_accept_optional_tenant_id_parameters() -> None:
    """Core ports that sit above or define the runtime boundary must not expose optional tenant_id."""
    ports_root = Path("src/doge/core/ports")
    offenders: list[str] = []
    for path in ports_root.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        if "tenant_id: str | None" in source or "tenant_id=None" in source or "tenant_id: str | None = None" in source:
            offenders.append(path.name)

    assert offenders == []
