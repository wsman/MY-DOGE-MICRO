"""Presentation helpers + small shared utilities for the session CLI command.

This is a leaf module: it imports no other ``session_*`` module, so the
embedded/gateway/interactive sub-modules can import these helpers freely.
The runtime container is resolved lazily through the ``session`` dispatcher
module so tests that monkeypatch ``session._runtime_container`` keep working.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from doge.core.security import redact_secrets


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


def print_last_run(run_id: str | None, *, field: str) -> None:
    if run_id is None:
        print("no active run")
        return
    from doge.interfaces.cli.commands import session as _session

    run = _session._runtime_container().build_resume_run_use_case().execute(run_id)
    if run is None:
        print("run not found")
        return
    items = getattr(run, field)
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
