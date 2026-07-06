"""CLI command: run."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from doge.bootstrap import build_runtime_container
from doge.core.security import redact_secrets
from doge.interfaces.cli.run_status_labels import next_actions_for_run_status


def cmd_run(args) -> None:
    """Execute one persisted research-agent run."""
    try:
        if getattr(args, "resume", None):
            if getattr(args, "deny", False) and not getattr(args, "approval", None):
                print("run failed: --deny requires --approval", file=sys.stderr)
                sys.exit(2)
                return
            run = asyncio.run(_runtime_container().build_resume_run_use_case().execute(
                args.resume,
                approval_id=getattr(args, "approval", None),
                approved=not getattr(args, "deny", False),
            ))
        else:
            if getattr(args, "approval", None) or getattr(args, "deny", False):
                print("run failed: --approval/--deny require --resume", file=sys.stderr)
                sys.exit(2)
                return
            if not getattr(args, "question", None):
                print("run failed: question is required unless --resume is provided", file=sys.stderr)
                sys.exit(2)
                return
            run = asyncio.run(_runtime_container().build_execute_run_use_case().execute(
                args.question,
                session_id=args.session,
                market=args.market,
                language=args.language,
                portfolio_id=args.portfolio,
                model_policy={"max_tool_rounds": args.max_tool_rounds},
            ))
    except Exception as exc:  # noqa: BLE001 - CLI emits concise operator message
        print(f"run failed: {exc}", file=sys.stderr)
        sys.exit(1)
        return

    payload = _serialize(run)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
        return
    if getattr(args, "jsonl", False):
        print(json.dumps(_run_jsonl_summary(run), ensure_ascii=False, sort_keys=True))
        _print_run_events(run, jsonl=True)
        return

    print(f"run_id={run.run_id}")
    print(f"status={run.status.value}")
    if run.artifacts:
        print(f"artifact={run.artifacts[-1].title}")
    if run.approvals:
        pending = [approval for approval in run.approvals if approval.status == "pending"]
        if pending:
            print("pending_approvals=" + ",".join(approval.approval_id for approval in pending))
    actions = next_actions_for_run_status(_status_value(run))
    if actions:
        print("Next actions:")
        for action in actions:
            print(f"  - {action}")
    if args.trace or getattr(args, "follow", False):
        _print_run_events(run, jsonl=False)


def _serialize(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj):
        return {key: _serialize(value) for key, value in asdict(obj).items()}
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _serialize(value) for key, value in obj.items()}
    return obj


def _status_value(run: Any) -> str:
    status = getattr(run, "status", None)
    if isinstance(status, Enum):
        return status.value
    return str(getattr(status, "value", status))


def _run_jsonl_summary(run: Any) -> dict[str, Any]:
    artifacts = getattr(run, "artifacts", []) or []
    latest_artifact = artifacts[-1] if artifacts else None
    return redact_secrets({
        "type": "run_summary",
        "run_id": getattr(run, "run_id", None),
        "status": _status_value(run),
        "artifact": getattr(latest_artifact, "title", None) if latest_artifact else None,
    })


def _event_type_value(event: Any) -> str:
    if isinstance(event, dict):
        value = event.get("event_type") or event.get("type")
    else:
        value = getattr(event, "event_type", None)
    if isinstance(value, Enum):
        return value.value
    return str(getattr(value, "value", value))


def _event_sequence(event: Any) -> Any:
    if isinstance(event, dict):
        return event.get("sequence", 0)
    return getattr(event, "sequence", 0)


def _event_payload(event: Any) -> Any:
    if isinstance(event, dict):
        return event.get("payload", event)
    return getattr(event, "payload", {})


def _print_run_events(run: Any, *, jsonl: bool) -> None:
    for event in getattr(run, "events", []) or []:
        if jsonl:
            record = {
                "type": "event",
                "run_id": getattr(run, "run_id", None),
                "event": _serialize(event),
            }
            print(json.dumps(redact_secrets(record), ensure_ascii=False, sort_keys=True))
            continue
        payload = json.dumps(redact_secrets(_event_payload(event)), ensure_ascii=False, sort_keys=True)
        print(f"{_event_sequence(event)}\t{_event_type_value(event)}\t{payload}")


def _runtime_container():
    return build_runtime_container()
