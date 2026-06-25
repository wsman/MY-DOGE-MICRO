"""Interactive REPL for the session CLI command (embedded + gateway)."""

from __future__ import annotations

import asyncio

from doge.application.services.file_upload_service import FileUploadError
from doge.interfaces.cli.commands.session_embedded import resolve_embedded_approval
from doge.interfaces.cli.commands.session_gateway import (
    GatewayArgs,
    gateway_create_session,
    gateway_create_turn,
    print_gateway_run_field,
    print_gateway_stream,
    gateway_upload_document,
    resolve_gateway_approval,
)
from doge.interfaces.cli.commands.session_presenter import (
    print_last_run,
    print_pending_approvals,
    print_run_summary,
)


def interactive_loop(
    session_id: str,
    market: str,
    *,
    mode: str = "embedded",
    daemon_url: str = "http://127.0.0.1:8901",
    api_token: str | None = None,
) -> None:
    from doge.interfaces.cli.commands import session as _session

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
                session = gateway_create_session(
                    GatewayArgs(daemon_url=daemon_url, api_token=api_token),
                    title="Research session",
                )
                session_id = session["session_id"]
            else:
                session = _session._runtime_container().build_create_session_use_case().execute()
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
                    document = gateway_upload_document(
                        GatewayArgs(daemon_url=daemon_url, api_token=api_token),
                        path,
                    )
                else:
                    document = _session._gateway_container().build_file_upload_service().register_path(path)
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
            registry = _session._runtime_container().build_default_tool_registry()
            print("\n".join(schema["function"]["name"] for schema in registry.schemas))
            continue
        if line == "/trace":
            if mode == "gateway":
                print_gateway_run_field(
                    GatewayArgs(daemon_url=daemon_url, api_token=api_token),
                    last_run_id,
                    field="events",
                )
            else:
                print_last_run(last_run_id, field="events")
            continue
        if line == "/artifacts":
            if mode == "gateway":
                print_gateway_run_field(
                    GatewayArgs(daemon_url=daemon_url, api_token=api_token),
                    last_run_id,
                    field="artifacts",
                )
            else:
                print_last_run(last_run_id, field="artifacts")
            continue
        if line.startswith("/approve ") or line.startswith("/deny "):
            if last_run_id is None:
                print("no active run")
                continue
            approval_id = line.split(maxsplit=1)[1]
            approved = line.startswith("/approve ")
            if mode == "gateway":
                resolve_gateway_approval(
                    GatewayArgs(daemon_url=daemon_url, api_token=api_token),
                    last_run_id,
                    approval_id,
                    approved,
                )
                continue
            try:
                run = resolve_embedded_approval(last_run_id, approval_id, approved)
            except KeyError as exc:
                print(f"approval_error={exc}")
                continue
            last_run_id = run.run_id
            print_run_summary(run)
            continue
        if line == "/save":
            print(f"session_id={session_id}")
            continue
        if mode == "gateway":
            run_id = gateway_create_turn(
                GatewayArgs(daemon_url=daemon_url, api_token=api_token),
                session_id,
                line,
                market=market,
                document_ids=document_ids,
                portfolio_id=portfolio_id,
            )
            last_run_id = run_id
            print(f"run_id={run_id} status=accepted")
            print_gateway_stream(GatewayArgs(daemon_url=daemon_url, api_token=api_token), run_id)
            continue
        run = asyncio.run(_session._runtime_container().build_execute_run_use_case().execute(
            line,
            session_id=session_id,
            market=market,
            document_ids=document_ids,
            portfolio_id=portfolio_id,
        ))
        last_run_id = run.run_id
        print(f"run_id={run.run_id} status={run.status.value}")
        print_pending_approvals(run, session_id=session_id, mode=mode)
