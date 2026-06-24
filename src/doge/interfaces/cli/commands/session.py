"""CLI command: session."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict, is_dataclass
from typing import Any

from doge.application.services.file_upload_service import FileUploadError
from doge.bootstrap import build_gateway_container, build_runtime_container
from doge.core.security import redact_secrets
from doge.shared.scope import TenantScope


def cmd_session(args) -> None:
    """Create, list, or resume persisted agent sessions."""
    if getattr(args, "mode", "embedded") == "gateway":
        _cmd_gateway_session(args)
        return

    if getattr(args, "list", False):
        sessions = _runtime_container().build_list_sessions_use_case().execute(limit=args.limit)
        for session in sessions:
            print(f"{session.session_id}\t{session.title}\tturns={len(session.turns)}\tupdated={session.updated_at}")
        return

    resume_id = getattr(args, "resume", None)
    if resume_id:
        session = _runtime_container().build_resume_session_use_case().execute(resume_id)
        if session is None:
            print(f"session not found: {resume_id}", file=sys.stderr)
            sys.exit(1)
        approval_ref = getattr(args, "approve", None) or getattr(args, "deny", None)
        if approval_ref:
            approved = getattr(args, "approve", None) is not None
            run_id, approval_id = _parse_approval_ref(approval_ref)
            if run_id is None:
                run_id = _find_run_for_approval(session, approval_id)
            if run_id is None:
                print(f"approval not found in session: {approval_id}", file=sys.stderr)
                sys.exit(1)
            if getattr(args, "mode", "embedded") == "gateway":
                _resolve_gateway_approval(args, run_id, approval_id, approved)
                return
            run = _resolve_embedded_approval(run_id, approval_id, approved)
            _print_run_summary(run)
            return
        message = getattr(args, "message", None)
        if message:
            run = asyncio.run(_runtime_container().build_execute_run_use_case().execute(
                message,
                session_id=session.session_id,
                market=args.market,
            ))
            print(f"run_id={run.run_id} status={run.status.value}")
            return
        print(f"session_id={session.session_id}")
        print(f"title={session.title}")
        if not session.turns:
            print("turns=0")
        for turn in session.turns:
            print(f"{turn.turn_id}\t{turn.run_id or '-'}\t{turn.user_message}")
        if getattr(args, "interactive", False):
            _interactive_loop(
                session.session_id,
                args.market,
                mode=getattr(args, "mode", "embedded"),
                daemon_url=getattr(args, "daemon_url", "http://127.0.0.1:8901"),
                api_token=getattr(args, "api_token", None),
            )
        return

    session = _runtime_container().build_create_session_use_case().execute(title=args.title)
    print(f"session_id={session.session_id}")
    print(f"title={session.title}")


def _cmd_gateway_session(args) -> None:
    if getattr(args, "list", False):
        sessions = _gateway_list_sessions(args, limit=args.limit)
        for session in sessions:
            print(
                f"{session.get('session_id')}\t{session.get('title')}\t"
                f"turns={len(session.get('turns', []))}\tupdated={session.get('updated_at', '-')}"
            )
        return

    resume_id = getattr(args, "resume", None)
    if resume_id:
        try:
            session = _gateway_get_session(args, resume_id)
        except Exception as exc:  # noqa: BLE001 - CLI emits concise operator message
            print(f"gateway_session_error={exc}", file=sys.stderr)
            sys.exit(1)
        approval_ref = getattr(args, "approve", None) or getattr(args, "deny", None)
        if approval_ref:
            approved = getattr(args, "approve", None) is not None
            run_id, approval_id = _parse_approval_ref(approval_ref)
            if run_id is None:
                print("gateway approval requires run_id:approval_id", file=sys.stderr)
                sys.exit(1)
            _resolve_gateway_approval(args, run_id, approval_id, approved)
            return
        message = getattr(args, "message", None)
        if message:
            run_id = _gateway_create_turn(args, resume_id, message, market=args.market)
            print(f"run_id={run_id} status=accepted")
            print(f"stream_via=GET /v1/runs/{run_id}/stream")
            return
        print(f"session_id={session.get('session_id')}")
        print(f"title={session.get('title')}")
        turns = session.get("turns", [])
        if not turns:
            print("turns=0")
        for turn in turns:
            print(f"{turn.get('turn_id')}\t{turn.get('run_id') or '-'}\t{turn.get('user_message')}")
        if getattr(args, "interactive", False):
            _interactive_loop(
                resume_id,
                args.market,
                mode="gateway",
                daemon_url=getattr(args, "daemon_url", "http://127.0.0.1:8901"),
                api_token=getattr(args, "api_token", None),
            )
        return

    session = _gateway_create_session(args, title=args.title)
    print(f"session_id={session.get('session_id')}")
    print(f"title={session.get('title')}")


def _interactive_loop(
    session_id: str,
    market: str,
    *,
    mode: str = "embedded",
    daemon_url: str = "http://127.0.0.1:8901",
    api_token: str | None = None,
) -> None:
    print("Enter a question, or /exit.")
    document_ids: list[str] = []
    portfolio_id: str | None = None
    last_run_id: str | None = None
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            return
        if not line:
            continue
        if line in {"/exit", "/quit"}:
            return
        if line == "/new":
            if mode == "gateway":
                session = _gateway_create_session(
                    _GatewayArgs(daemon_url=daemon_url, api_token=api_token),
                    title="Research session",
                )
                session_id = session["session_id"]
            else:
                session = _runtime_container().build_create_session_use_case().execute()
                session_id = session.session_id
            last_run_id = None
            print(f"session_id={session_id}")
            continue
        if line.startswith("/resume "):
            session_id = line.split(maxsplit=1)[1]
            last_run_id = None
            print(f"session_id={session_id}")
            continue
        if line.startswith("/attach "):
            path = line.split(maxsplit=1)[1]
            try:
                if mode == "gateway":
                    document = _gateway_upload_document(
                        _GatewayArgs(daemon_url=daemon_url, api_token=api_token),
                        path,
                    )
                else:
                    document = _gateway_container().build_file_upload_service().register_path(path)
            except FileUploadError as exc:
                print(f"attach_error={exc}")
                continue
            except Exception as exc:  # noqa: BLE001 - gateway SDK errors are operator-facing
                print(f"attach_error={exc}")
                continue
            doc_id = document["document_id"]
            if doc_id not in document_ids:
                document_ids.append(doc_id)
            print(
                f"attached={doc_id} path={path} "
                f"status={document.get('parsing_status') or document.get('status')}"
            )
            continue
        if line.startswith("/portfolio "):
            portfolio_id = line.split(maxsplit=1)[1]
            print(f"portfolio={portfolio_id}")
            continue
        if line == "/tools":
            registry = _runtime_container().build_default_tool_registry()
            print("\n".join(schema["function"]["name"] for schema in registry.schemas))
            continue
        if line == "/trace":
            _print_last_run(last_run_id, field="events")
            continue
        if line == "/artifacts":
            _print_last_run(last_run_id, field="artifacts")
            continue
        if line.startswith("/approve ") or line.startswith("/deny "):
            if last_run_id is None:
                print("no active run")
                continue
            approval_id = line.split(maxsplit=1)[1]
            approved = line.startswith("/approve ")
            if mode == "gateway":
                _resolve_gateway_approval(
                    _GatewayArgs(daemon_url=daemon_url, api_token=api_token),
                    last_run_id,
                    approval_id,
                    approved,
                )
                continue
            try:
                run = _resolve_embedded_approval(last_run_id, approval_id, approved)
            except KeyError as exc:
                print(f"approval_error={exc}")
                continue
            last_run_id = run.run_id
            _print_run_summary(run)
            continue
        if line == "/save":
            print(f"session_id={session_id}")
            continue
        if mode == "gateway":
            run_id = _gateway_create_turn(
                _GatewayArgs(daemon_url=daemon_url, api_token=api_token),
                session_id,
                line,
                market=market,
                document_ids=document_ids,
                portfolio_id=portfolio_id,
            )
            last_run_id = run_id
            print(f"run_id={run_id} status=accepted")
            print(f"stream_via=GET /v1/runs/{run_id}/stream")
            continue
        run = asyncio.run(_runtime_container().build_execute_run_use_case().execute(
            line,
            session_id=session_id,
            market=market,
            document_ids=document_ids,
            portfolio_id=portfolio_id,
        ))
        last_run_id = run.run_id
        print(f"run_id={run.run_id} status={run.status.value}")
        _print_pending_approvals(run, session_id=session_id, mode=mode)


def _print_last_run(run_id: str | None, *, field: str) -> None:
    if run_id is None:
        print("no active run")
        return
    run = _runtime_container().build_resume_run_use_case().execute(run_id)
    if run is None:
        print("run not found")
        return
    items = getattr(run, field)
    if not items:
        print(f"{field}=0")
        return
    for item in items:
        print(json.dumps(redact_secrets(_to_cli_payload(item)), ensure_ascii=False, sort_keys=True))


def _to_cli_payload(item: Any) -> Any:
    if is_dataclass(item) and not isinstance(item, type):
        return asdict(item)
    if hasattr(item, "__dict__"):
        return vars(item)
    return item


def _resolve_embedded_approval(run_id: str, approval_id: str, approved: bool):
    runtime = _runtime_container().build_persisted_research_agent_runtime()
    run = asyncio.run(runtime.resolve_approval(TenantScope.local(), run_id, approval_id, approved))
    if approved:
        run = asyncio.run(runtime.run_to_pause_or_completion(run_id))
    return run


def _resolve_gateway_approval(args, run_id: str, approval_id: str, approved: bool) -> None:
    payload = _gateway_resolve_approval(args, run_id, approval_id, approved)
    status = payload.get("status") or payload.get("run", {}).get("status") or payload.get("status_code")
    print(f"gateway_approval_resolved run_id={run_id} approval_id={approval_id} approved={str(approved).lower()}")
    if status:
        print(f"status={status}")


def _gateway_create_turn(
    args,
    session_id: str,
    message: str,
    *,
    market: str = "us",
    document_ids: list[str] | None = None,
    portfolio_id: str | None = None,
) -> str:
    return _with_gateway_client(
        args,
        lambda client: client.sessions.create_turn(
            session_id,
            message,
            market=market,
            document_ids=document_ids or [],
            portfolio_id=portfolio_id,
            model_policy={"execution_profile": "financial_research"},
        ),
    )


def _gateway_list_sessions(args, *, limit: int) -> list[dict[str, Any]]:
    return _with_gateway_client(args, lambda client: client.sessions.list(limit=limit))


def _gateway_create_session(args, *, title: str) -> dict[str, Any]:
    return _with_gateway_client(args, lambda client: client.sessions.create(title=title).data)


def _gateway_get_session(args, session_id: str) -> dict[str, Any]:
    return _with_gateway_client(args, lambda client: client.sessions.get(session_id).data)


def _gateway_resolve_approval(args, run_id: str, approval_id: str, approved: bool) -> dict[str, Any]:
    return _with_gateway_client(args, lambda client: client.runs.approve(run_id, approval_id, approved))


def _gateway_upload_document(args, path: str) -> dict[str, Any]:
    return _with_gateway_client(args, lambda client: client.documents.upload_path(path))


def _with_gateway_client(args, operation):
    client = _gateway_client(args)
    try:
        return operation(client)
    finally:
        client.close()


def _gateway_client(args):
    DogeClient = _load_doge_client()
    return DogeClient(
        base_url=getattr(args, "daemon_url", "http://127.0.0.1:8901"),
        api_token=getattr(args, "api_token", None),
    )


def _load_doge_client():
    try:
        from doge_sdk import DogeClient

        return DogeClient
    except ModuleNotFoundError as exc:
        raise RuntimeError("gateway mode requires the doge-sdk Python package") from exc


def _print_pending_approvals(run, *, session_id: str, mode: str) -> None:
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


def _print_run_summary(run) -> None:
    print(f"run_id={run.run_id} status={run.status.value}")
    if getattr(run, "artifacts", None):
        print(f"artifact={run.artifacts[-1].title}")
    _print_pending_approvals(run, session_id=getattr(run, "session_id", "") or "-", mode="embedded")


def _parse_approval_ref(value: str) -> tuple[str | None, str]:
    if ":" not in value:
        return None, value
    run_id, approval_id = value.split(":", 1)
    return run_id or None, approval_id


def _find_run_for_approval(session, approval_id: str) -> str | None:
    resume_run = _runtime_container().build_resume_run_use_case()
    for turn in session.turns:
        if not turn.run_id:
            continue
        run = resume_run.execute(turn.run_id)
        if run is None:
            continue
        if any(approval.approval_id == approval_id for approval in run.approvals):
            return run.run_id
    return None


class _GatewayArgs:
    def __init__(self, *, daemon_url: str, api_token: str | None) -> None:
        self.daemon_url = daemon_url
        self.api_token = api_token


def _runtime_container():
    return build_runtime_container()


def _gateway_container():
    return build_gateway_container()
