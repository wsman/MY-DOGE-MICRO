"""CLI command: research case workspace."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from doge.application import composition
from doge.platform.workspace import (
    CaseDecisionCreate,
    CaseExecutionCreate,
    PlatformRequestContext,
    PlatformValidationError,
)


def cmd_case(args) -> None:
    """List, show, preflight, execute, review, or decide a research case."""
    service = composition.build_research_case_service()
    context = PlatformRequestContext()
    try:
        if args.case_cmd == "list":
            cases = service.list(context, project_id=args.project_id, limit=args.limit)
            _emit({"research_cases": [_serialize(item) for item in cases]}, json_only=args.json)
            return
        if args.case_cmd == "show":
            review = service.build_case_review(context, args.case_id)
            _emit(review, json_only=args.json)
            return
        if args.case_cmd == "preflight":
            preflight = service.preflight_template_execution(
                context,
                args.case_id,
                _case_execution_request(args, trigger_channel="cli"),
                workflow_templates_enabled=True,
            )
            _emit(preflight.to_dict(), json_only=args.json)
            return
        if args.case_cmd == "execute":
            result = asyncio.run(service.execute_template(
                context,
                args.case_id,
                _case_execution_request(args, trigger_channel="cli"),
                workflow_templates_enabled=True,
            ))
            _emit(result.to_dict(), json_only=args.json)
            return
        if args.case_cmd == "review":
            review = service.build_case_review(context, args.case_id)
            _emit(review, json_only=args.json)
            return
        if args.case_cmd == "decision":
            decision = service.record_decision(
                context,
                args.case_id,
                CaseDecisionCreate(
                    decision_type=args.decision,
                    rationale=args.rationale or "",
                    source_run_ids=args.source_run_id or [],
                    source_execution_ids=args.source_execution_id or [],
                ),
            )
            _emit(_serialize(decision), json_only=args.json)
            return
    except PlatformValidationError as exc:
        payload = {"error": str(exc), "details": exc.details}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
        else:
            print(f"case failed: {exc}", file=sys.stderr)
        sys.exit(1)
        return
    except Exception as exc:  # noqa: BLE001 - CLI emits concise operator message
        print(f"case failed: {exc}", file=sys.stderr)
        sys.exit(1)
        return

    print("case subcommand required", file=sys.stderr)
    sys.exit(2)


def _case_execution_request(args, *, trigger_channel: str) -> CaseExecutionCreate:
    return CaseExecutionCreate(
        template_id=args.template_id,
        question=args.question,
        workflow=args.workflow,
        session_id=args.session_id,
        market=args.market,
        language=args.language,
        document_ids=args.document_id or [],
        portfolio_id=args.portfolio_id,
        model_policy=_json_object(args.model_policy),
        inputs=_json_object(args.inputs),
        skip_preflight=getattr(args, "skip_preflight", False),
        trigger_channel=trigger_channel,
    )


def _json_object(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise PlatformValidationError("JSON value must be an object")
    return value


def _emit(payload: dict[str, Any], *, json_only: bool) -> None:
    payload = _serialize(payload)
    if json_only:
        print(json.dumps(payload, ensure_ascii=False))
        return
    if "research_cases" in payload:
        for item in payload["research_cases"]:
            print(f"{item['case_id']}\t{item['status']}\t{item['title']}")
        return
    if "execution_id" in payload:
        print(f"execution_id={payload.get('execution_id')}")
        print(f"status={payload.get('status')}")
        print(f"run_id={payload.get('run_id') or '-'}")
        return
    if "valid" in payload or "ok" in payload:
        print(f"valid={payload.get('valid', payload.get('ok'))}")
        for error in payload.get("errors", []):
            print(f"error={error}")
        for error in payload.get("input_errors", []):
            print(f"input_error={error}")
        for capability in payload.get("missing_capabilities", []):
            print(f"missing_capability={capability}")
        for warning in payload.get("warnings", []):
            print(f"warning={warning}")
        return
    if "case" in payload:
        case = payload.get("case") or {}
        print(f"case_id={case.get('case_id')}")
        print(f"title={case.get('title')}")
        print(f"executions={len(payload.get('executions', []))}")
        print(f"decisions={len(payload.get('decisions', []))}")
        return
    if "decision_id" in payload:
        print(f"decision_id={payload.get('decision_id')}")
        print(f"decision_type={payload.get('decision_type')}")
        return
    print(json.dumps(payload, ensure_ascii=False))


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
