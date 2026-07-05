"""Tests for the ``doge start`` first-run launcher (Sprint UX-1 Slice B, CLI-1).

Pins the launcher's contract: the ``start`` subparser exists with the documented
``--path`` choices; the menu renders all five paths; non-TTY stdin never hangs;
``demo``/``doctor`` dispatch inline while ``cli``/``daemon``/``web`` print
guidance; ``doge start`` itself introduces no new exit code.
"""

from __future__ import annotations

import argparse
from unittest.mock import patch

import pytest

from doge.interfaces.cli import main
from doge.interfaces.cli.commands.start import _PATH_KEYS, _PATHS, cmd_start
from doge.interfaces.cli.main import build_parser


def _args(path: str | None = None) -> argparse.Namespace:
    return argparse.Namespace(path=path)


def test_start_subparser_registered_with_documented_path_choices() -> None:
    parser = build_parser()
    sub = parser._subparsers._group_actions[0]
    assert "start" in sub.choices
    start_parser = sub.choices["start"]
    path_action = next(a for a in start_parser._actions if "--path" in a.option_strings)
    assert set(path_action.choices) == set(_PATH_KEYS)


def test_unknown_path_rejected_with_argparse_exit_2() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["start", "--path", "bogus"])
    assert exc.value.code == 2


def test_menu_renders_all_five_paths_without_hanging_on_non_tty(
    capsys, monkeypatch
) -> None:
    # Non-TTY stdin: the menu prints and returns without prompting (no hang).
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    cmd_start(_args(path=None))  # must not raise / block
    out = capsys.readouterr().out
    for _key, label, _desc, _cmd in _PATHS:
        assert label in out
    assert "doge start --path" in out


def test_path_demo_dispatches_inline_to_cmd_demo(monkeypatch) -> None:
    with patch("doge.interfaces.cli.commands.start.cmd_demo") as demo:
        cmd_start(_args(path="demo"))
    demo.assert_called_once()
    (call_args,) = demo.call_args.args
    assert call_args.market == "cn"
    assert call_args.top == 5


def test_path_doctor_dispatches_inline_to_cmd_doctor(monkeypatch) -> None:
    with patch("doge.interfaces.cli.commands.start.cmd_doctor") as doctor:
        cmd_start(_args(path="doctor"))
    doctor.assert_called_once()
    (call_args,) = doctor.call_args.args
    assert call_args.json is False
    assert call_args.next is True


def test_blocking_paths_print_command_without_dispatching(capsys, monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    for key in ("cli", "daemon", "web"):
        with patch("doge.interfaces.cli.commands.start.cmd_demo") as demo, patch(
            "doge.interfaces.cli.commands.start.cmd_doctor"
        ) as doctor:
            cmd_start(_args(path=key))
            demo.assert_not_called()
            doctor.assert_not_called()
    out = capsys.readouterr().out
    # Each blocking path prints its exact command (guidance), not a dispatch.
    assert "doge session --interactive" in out
    assert "doged serve" in out
    assert "npm run dev" in out
    assert "http://127.0.0.1:5173" in out
    assert "http://127.0.0.1:8901" not in out


def test_menu_path_introduces_no_nonzero_exit(capsys, monkeypatch) -> None:
    # The menu path returns normally (no SystemExit) — exit code 0 is implicit.
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    cmd_start(_args(path=None))
