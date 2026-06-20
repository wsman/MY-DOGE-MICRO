"""CLI command: session."""

from __future__ import annotations

import asyncio
import sys

from doge.application import composition


def cmd_session(args) -> None:
    """Create, list, or resume persisted agent sessions."""
    if getattr(args, "list", False):
        sessions = composition.build_list_sessions_use_case().execute(limit=args.limit)
        for session in sessions:
            print(f"{session.session_id}\t{session.title}\tturns={len(session.turns)}\tupdated={session.updated_at}")
        return

    resume_id = getattr(args, "resume", None)
    if resume_id:
        session = composition.build_resume_session_use_case().execute(resume_id)
        if session is None:
            print(f"session not found: {resume_id}", file=sys.stderr)
            sys.exit(1)
        message = getattr(args, "message", None)
        if message:
            run = asyncio.run(composition.build_execute_run_use_case().execute(
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
            _interactive_loop(session.session_id, args.market)
        return

    session = composition.build_create_session_use_case().execute(title=args.title)
    print(f"session_id={session.session_id}")
    print(f"title={session.title}")


def _interactive_loop(session_id: str, market: str) -> None:
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
            session = composition.build_create_session_use_case().execute()
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
            doc_id = f"doc-{len(document_ids) + 1}"
            document_ids.append(doc_id)
            print(f"attached={doc_id} path={path}")
            continue
        if line.startswith("/portfolio "):
            portfolio_id = line.split(maxsplit=1)[1]
            print(f"portfolio={portfolio_id}")
            continue
        if line == "/tools":
            registry = composition.build_default_tool_registry()
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
            print("approval continuation is unsupported in the CLI; use the /v1 daemon API")
            continue
        if line == "/save":
            print(f"session_id={session_id}")
            continue
        run = asyncio.run(composition.build_execute_run_use_case().execute(
            line,
            session_id=session_id,
            market=market,
            document_ids=document_ids,
            portfolio_id=portfolio_id,
        ))
        last_run_id = run.run_id
        print(f"run_id={run.run_id} status={run.status.value}")


def _print_last_run(run_id: str | None, *, field: str) -> None:
    if run_id is None:
        print("no active run")
        return
    run = composition.build_resume_run_use_case().execute(run_id)
    if run is None:
        print("run not found")
        return
    items = getattr(run, field)
    if not items:
        print(f"{field}=0")
        return
    for item in items:
        print(item)
