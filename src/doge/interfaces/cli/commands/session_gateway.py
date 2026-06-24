"""Gateway-mode session command (doge-sdk client calls)."""

from __future__ import annotations

import sys
from typing import Any

from doge.interfaces.cli.commands.session_presenter import parse_approval_ref


class GatewayArgs:
    """Minimal args shim for gateway calls driven from the interactive loop."""

    def __init__(self, *, daemon_url: str, api_token: str | None) -> None:
        self.daemon_url = daemon_url
        self.api_token = api_token


def with_gateway_client(args, operation):
    from doge.interfaces.cli.commands import session as _session

    client = _session._gateway_client(args)
    try:
        return operation(client)
    finally:
        client.close()


def gateway_create_turn(
    args,
    session_id: str,
    message: str,
    *,
    market: str = "us",
    document_ids: list[str] | None = None,
    portfolio_id: str | None = None,
) -> str:
    return with_gateway_client(
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


def gateway_list_sessions(args, *, limit: int) -> list[dict[str, Any]]:
    return with_gateway_client(args, lambda client: client.sessions.list(limit=limit))


def gateway_create_session(args, *, title: str) -> dict[str, Any]:
    return with_gateway_client(args, lambda client: client.sessions.create(title=title).data)


def gateway_get_session(args, session_id: str) -> dict[str, Any]:
    return with_gateway_client(args, lambda client: client.sessions.get(session_id).data)


def gateway_resolve_approval(args, run_id: str, approval_id: str, approved: bool) -> dict[str, Any]:
    return with_gateway_client(args, lambda client: client.runs.approve(run_id, approval_id, approved))


def gateway_upload_document(args, path: str) -> dict[str, Any]:
    return with_gateway_client(args, lambda client: client.documents.upload_path(path))


def resolve_gateway_approval(args, run_id: str, approval_id: str, approved: bool) -> None:
    payload = gateway_resolve_approval(args, run_id, approval_id, approved)
    status = payload.get("status") or payload.get("run", {}).get("status") or payload.get("status_code")
    print(f"gateway_approval_resolved run_id={run_id} approval_id={approval_id} approved={str(approved).lower()}")
    if status:
        print(f"status={status}")


def cmd_gateway_session(args) -> None:
    if getattr(args, "list", False):
        sessions = gateway_list_sessions(args, limit=args.limit)
        for session in sessions:
            print(
                f"{session.get('session_id')}\t{session.get('title')}\t"
                f"turns={len(session.get('turns', []))}\tupdated={session.get('updated_at', '-')}"
            )
        return

    resume_id = getattr(args, "resume", None)
    if resume_id:
        try:
            session = gateway_get_session(args, resume_id)
        except Exception as exc:  # noqa: BLE001 - CLI emits concise operator message
            print(f"gateway_session_error={exc}", file=sys.stderr)
            sys.exit(1)
        approval_ref = getattr(args, "approve", None) or getattr(args, "deny", None)
        if approval_ref:
            approved = getattr(args, "approve", None) is not None
            run_id, approval_id = parse_approval_ref(approval_ref)
            if run_id is None:
                print("gateway approval requires run_id:approval_id", file=sys.stderr)
                sys.exit(1)
            resolve_gateway_approval(args, run_id, approval_id, approved)
            return
        message = getattr(args, "message", None)
        if message:
            run_id = gateway_create_turn(args, resume_id, message, market=args.market)
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
            from doge.interfaces.cli.commands.session_interactive import interactive_loop

            interactive_loop(
                resume_id,
                args.market,
                mode="gateway",
                daemon_url=getattr(args, "daemon_url", "http://127.0.0.1:8901"),
                api_token=getattr(args, "api_token", None),
            )
        return

    session = gateway_create_session(args, title=args.title)
    print(f"session_id={session.get('session_id')}")
    print(f"title={session.get('title')}")
