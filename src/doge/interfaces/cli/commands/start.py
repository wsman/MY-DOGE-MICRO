"""CLI command: start — first-run launcher (Sprint UX-1 Slice B, CLI-1).

Routes a first-time operator to the five main paths without requiring them to
memorize subcommands. ``demo`` and ``doctor`` dispatch inline to their existing
handlers; ``cli``, ``daemon``, and ``web`` print the exact command to run
(routing guidance) rather than spawning a nested interactive loop or a
long-running daemon process — the launcher itself stays non-blocking and
testable.

``doge start`` itself never exits non-zero: an unknown ``--path`` is rejected by
argparse (exit 2), and an inlined ``demo``/``doctor`` propagates its own
documented exit code (1 on no-data / not-ready).
"""

from __future__ import annotations

import argparse
import sys

# Import sibling command modules directly (not via the ``commands`` package) to
# avoid an import cycle: ``commands/__init__`` imports this module.
from doge.interfaces.cli.commands.demo import cmd_demo
from doge.interfaces.cli.commands.doctor import cmd_doctor

# (key, label, description, exact command to run).
_PATHS: list[tuple[str, str, str, str]] = [
    (
        "cli",
        "Local CLI session",
        "Interactive research session in the terminal.",
        "doge session --interactive",
    ),
    (
        "daemon",
        "Start daemon",
        "Persisted runtime gateway on 127.0.0.1:8901.",
        "doged serve --port 8901",
    ),
    (
        "web",
        "Open Web workspace",
        "Research workspace in your browser (run alongside the daemon).",
        "cd web && npm run dev   (then open http://127.0.0.1:5173)",
    ),
    (
        "demo",
        "Run demo",
        "5-minute demo using bundled sample data (no API key).",
        "doge demo",
    ),
    (
        "doctor",
        "Check readiness",
        "Local diagnostics.",
        "doge doctor --next",
    ),
]

_PATH_KEYS = [key for key, *_ in _PATHS]


def _print_menu() -> None:
    print("=" * 60)
    print("MY-DOGE-MICRO — choose a path:")
    print("=" * 60)
    for index, (_key, label, desc, _cmd) in enumerate(_PATHS, start=1):
        print(f"  {index}. {label} — {desc}")
    print()
    print("Non-interactive: doge start --path <name>")
    print(f"  names: {', '.join(_PATH_KEYS)}")


def _dispatch(key: str) -> None:
    """Route one path. ``demo``/``doctor`` run inline; the others print guidance."""
    label, _desc, command = next(
        (label, desc, cmd) for k, label, desc, cmd in _PATHS if k == key
    )
    if key == "demo":
        print(f"-> {label}\n  running: {command}\n")
        cmd_demo(argparse.Namespace(market="cn", top=5))
        return
    if key == "doctor":
        print(f"-> {label}\n  running: {command}\n")
        cmd_doctor(argparse.Namespace(json=False, next=True))
        return
    # cli / daemon / web are blocking or interactive — print guidance only so
    # the launcher never spawns a nested loop or long-running process.
    print(f"-> {label}\n  run: {command}")


def cmd_start(args) -> None:
    """First-run launcher: print a 5-path menu or dispatch ``--path <name>``."""
    path = getattr(args, "path", None)
    if path:
        _dispatch(path)
        return
    _print_menu()
    # Non-interactive (no TTY / stdin closed): print the menu and return without
    # blocking on input() so CI and subprocess callers never hang.
    if not sys.stdin.isatty():
        return
    try:
        choice = input("\nEnter a number (1-5), or Enter to exit: ").strip()
    except EOFError:
        return
    if not choice:
        return
    index = int(choice) - 1 if choice.isdigit() else -1
    if not 0 <= index < len(_PATHS):
        print(
            f"Unknown choice {choice!r}. Use: doge start --path <name> "
            f"(names: {', '.join(_PATH_KEYS)})"
        )
        return
    _dispatch(_PATHS[index][0])
