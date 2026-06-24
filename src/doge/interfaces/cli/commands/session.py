"""CLI command: session (dispatcher + compatibility entrypoint).

The session command is split into focused sub-modules:
- ``session_embedded``  in-process (embedded) mode + embedded approval flow
- ``session_gateway``   gateway mode backed by the doge-sdk client
- ``session_interactive`` the interactive REPL (embedded + gateway)
- ``session_presenter``  presentation helpers + shared parsing utilities

This module keeps the public ``cmd_session`` dispatcher, owns the process
container / SDK-client accessors that tests monkeypatch, and re-exports the
sub-module callables under their original ``_``-prefixed names so existing
callers and tests that reference ``session.<name>`` keep working unchanged.
"""

from __future__ import annotations

from doge.bootstrap import build_gateway_container, build_runtime_container
from doge.interfaces.cli.commands.session_embedded import cmd_embedded_session
from doge.interfaces.cli.commands.session_gateway import (
    GatewayArgs,
    cmd_gateway_session,
    resolve_gateway_approval,
)
from doge.interfaces.cli.commands.session_interactive import interactive_loop
from doge.interfaces.cli.commands.session_presenter import (
    parse_approval_ref,
    print_last_run,
    print_pending_approvals,
    print_run_summary,
    to_cli_payload,
)


def cmd_session(args) -> None:
    """Create, list, or resume persisted agent sessions."""
    if getattr(args, "mode", "embedded") == "gateway":
        cmd_gateway_session(args)
        return
    cmd_embedded_session(args)


# ── Patchable container / SDK-client accessors ──
# Tests monkeypatch these on this module; the sub-modules resolve them lazily
# through ``session`` so the patches take effect across the split.

def _runtime_container():
    return build_runtime_container()


def _gateway_container():
    return build_gateway_container()


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


# ── Compatibility re-exports (original ``_``-prefixed names) ──
_interactive_loop = interactive_loop
_cmd_gateway_session = cmd_gateway_session
_resolve_gateway_approval = resolve_gateway_approval
_print_pending_approvals = print_pending_approvals
_print_last_run = print_last_run
