"""Presentation helpers + small shared utilities for the session CLI command.

This is a leaf module: it imports no other ``session_*`` module, so the
embedded/gateway/interactive sub-modules can import these helpers freely.
The runtime container is resolved lazily through the ``session`` dispatcher
module so tests that monkeypatch ``session._runtime_container`` keep working.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any, Protocol

from doge.core.security import redact_secrets


class RunClient(Protocol):
    def get_run(self, run_id: str) -> Any | None:
        """Return a run payload from either the embedded runtime or SDK."""
        ...


class EmbeddedRunClient:
    def __init__(self, get_run_use_case: Any) -> None:
        self._get_run = get_run_use_case

    def get_run(self, run_id: str) -> Any | None:
        return self._get_run.execute(run_id)


class SdkRunClient:
    def __init__(self, sdk_client: Any) -> None:
        self._sdk_client = sdk_client

    def get_run(self, run_id: str) -> Any | None:
        return self._sdk_client.runs.get(run_id)


def to_cli_payload(item: Any) -> Any:
    if is_dataclass(item) and not isinstance(item, type):
        return asdict(item)
    if hasattr(item, "__dict__"):
        return vars(item)
    return item


def parse_approval_ref(value: str) -> tuple[str | None, str]:
    if ":" not in value:
        return None, value
    run_id, approval_id = value.split(":", 1)
    return run_id or None, approval_id


def build_embedded_run_client() -> EmbeddedRunClient:
    from doge.interfaces.cli.commands import session as _session

    container = _session._runtime_container()
    return EmbeddedRunClient(container.build_get_run_snapshot_use_case())


def _run_field(run: Any, field: str) -> Any:
    if isinstance(run, dict):
        return run.get(field)
    return getattr(run, field)


def print_last_run(run_id: str | None, *, field: str, client: RunClient | None = None) -> None:
    if run_id is None:
        print("no active run")
        return

    run_client = client or build_embedded_run_client()
    run = run_client.get_run(run_id)
    if run is None:
        print("run not found")
        return
    items = _run_field(run, field)
    if not items:
        print(f"{field}=0")
        return
    for item in items:
        print(json.dumps(redact_secrets(to_cli_payload(item)), ensure_ascii=False, sort_keys=True))


def print_pending_approvals(run, *, session_id: str, mode: str) -> None:
    pending = [approval for approval in getattr(run, "approvals", []) if getattr(approval, "status", "pending") == "pending"]
    for approval in pending:
        approval_id = getattr(approval, "approval_id", "")
        print(
            "approval_required "
            f"run_id={run.run_id} approval_id={approval_id} "
            f"action={getattr(approval, 'action', '')} risk_level={getattr(approval, 'risk_level', '')}"
        )
        if mode == "gateway":
            print(f"resolve_via=POST /v1/runs/{run.run_id}/approvals/{approval_id} {{\"approved\": true}}")
            print(f"resume_via=doge session --mode gateway --resume {session_id} --approve {run.run_id}:{approval_id}")
        else:
            print(f"resolve_via=/approve {approval_id}")


def print_run_summary(run) -> None:
    print(f"run_id={run.run_id} status={run.status.value}")
    if getattr(run, "artifacts", None):
        print(f"artifact={run.artifacts[-1].title}")
    print_pending_approvals(run, session_id=getattr(run, "session_id", "") or "-", mode="embedded")
