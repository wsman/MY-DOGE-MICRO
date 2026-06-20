"""CLI command: run."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from doge.application import composition


def cmd_run(args) -> None:
    """Execute one persisted research-agent run."""
    try:
        run = asyncio.run(composition.build_execute_run_use_case().execute(
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

    print(f"run_id={run.run_id}")
    print(f"status={run.status.value}")
    if run.artifacts:
        print(f"artifact={run.artifacts[-1].title}")
    if run.approvals:
        pending = [approval for approval in run.approvals if approval.status == "pending"]
        if pending:
            print("pending_approvals=" + ",".join(approval.approval_id for approval in pending))
    if args.trace:
        for event in run.events:
            print(f"{event.sequence}\t{event.event_type.value}\t{json.dumps(event.payload, ensure_ascii=False)}")


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
