"""Embedded-mode session command (in-process runtime)."""

from __future__ import annotations

import asyncio
import sys

from doge.interfaces.cli.commands.session_presenter import (
    parse_approval_ref,
    print_run_summary,
)
from doge.shared.scope import TenantScope


def resolve_embedded_approval(run_id: str, approval_id: str, approved: bool):
    from doge.interfaces.cli.commands import session as _session

    runtime = _session._runtime_container().build_persisted_research_agent_runtime()
    scope = TenantScope.local()
    run = asyncio.run(runtime.resolve_approval(scope, run_id, approval_id, approved))
    if approved:
        run = asyncio.run(runtime.run_to_pause_or_completion(scope, run_id))
    return run


def cancel_embedded_run(run_id: str):
    from doge.interfaces.cli.commands import session as _session

    runtime = _session._runtime_container().build_persisted_research_agent_runtime()
    return asyncio.run(runtime.cancel_run(TenantScope.local(), run_id))


def find_run_for_approval(session, approval_id: str) -> str | None:
    from doge.interfaces.cli.commands import session as _session

    resume_run = _session._runtime_container().build_resume_run_use_case()
    for turn in session.turns:
        if not turn.run_id:
            continue
        run = resume_run.execute(turn.run_id)
        if run is None:
            continue
        if any(approval.approval_id == approval_id for approval in run.approvals):
            return run.run_id
    return None


def cmd_embedded_session(args) -> None:
    """Create, list, or resume a persisted agent session in embedded mode."""
    from doge.interfaces.cli.commands import session as _session

    cancel_run_id = getattr(args, "cancel", None)
    if cancel_run_id:
        run = cancel_embedded_run(cancel_run_id)
        print_run_summary(run)
        return

    if getattr(args, "list", False):
        sessions = _session._runtime_container().build_list_sessions_use_case().execute(limit=args.limit)
        for session in sessions:
            print(f"{session.session_id}\t{session.title}\tturns={len(session.turns)}\tupdated={session.updated_at}")
        return

    resume_id = getattr(args, "resume", None)
    if resume_id:
        session = _session._runtime_container().build_resume_session_use_case().execute(resume_id)
        if session is None:
            print(f"session not found: {resume_id}", file=sys.stderr)
            sys.exit(1)
        approval_ref = getattr(args, "approve", None) or getattr(args, "deny", None)
        if approval_ref:
            approved = getattr(args, "approve", None) is not None
            run_id, approval_id = parse_approval_ref(approval_ref)
            if run_id is None:
                run_id = find_run_for_approval(session, approval_id)
            if run_id is None:
                print(f"approval not found in session: {approval_id}", file=sys.stderr)
                sys.exit(1)
            run = resolve_embedded_approval(run_id, approval_id, approved)
            print_run_summary(run)
            return
        message = getattr(args, "message", None)
        if message:
            run = asyncio.run(_session._runtime_container().build_execute_run_use_case().execute(
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
            from doge.interfaces.cli.commands.session_interactive import interactive_loop

            interactive_loop(
                session.session_id,
                args.market,
                mode="embedded",
                daemon_url=getattr(args, "daemon_url", "http://127.0.0.1:8901"),
                api_token=getattr(args, "api_token", None),
            )
        return

    session = _session._runtime_container().build_create_session_use_case().execute(title=args.title)
    print(f"session_id={session.session_id}")
    print(f"title={session.title}")
