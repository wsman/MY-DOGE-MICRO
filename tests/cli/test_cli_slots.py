"""CLI tests for ``doge slots`` (ADR-0042)."""

from __future__ import annotations

import json

import pytest

from doge.config import reset_settings
from doge.interfaces.cli.main import build_parser, main

_FEATURE_VARS = [
    "DOGE_FEATURE_RUN_SUMMARY_API",
    "DOGE_FEATURE_PLATFORM_OBJECTS",
    "DOGE_FEATURE_WORKFLOW_TEMPLATES",
    "DOGE_FEATURE_CAPABILITY_REGISTRY",
    "DOGE_FEATURE_RUNTIME_OUTBOX_PUBLISHER",
    "DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED",
    "DOGE_FEATURE_SLOT_PLATFORM",
]


def _strip_feature_env(monkeypatch) -> None:
    for var in _FEATURE_VARS:
        monkeypatch.delenv(var, raising=False)


def test_parser_accepts_slots_list_and_show() -> None:
    parser = build_parser()
    list_args = parser.parse_args(["slots", "list"])
    assert list_args.cmd == "slots"
    assert list_args.slots_cmd == "list"
    assert list_args.json is False

    show_args = parser.parse_args(["slots", "show", "market.core", "--json"])
    assert show_args.slots_cmd == "show"
    assert show_args.slot_id == "market.core"
    assert show_args.json is True


def test_parser_requires_slots_subcommand() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["slots"])  # required subparser missing -> argparse error


def test_list_flag_off_prints_disabled_message(monkeypatch, capsys) -> None:
    _strip_feature_env(monkeypatch)
    reset_settings()
    main(["slots", "list"])
    out = capsys.readouterr().out
    assert "disabled" in out
    assert "DOGE_FEATURE_SLOT_PLATFORM" in out


def test_list_flag_off_json_payload(monkeypatch, capsys) -> None:
    _strip_feature_env(monkeypatch)
    reset_settings()
    main(["slots", "list", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"status": "disabled", "feature_flag": "DOGE_FEATURE_SLOT_PLATFORM"}


def test_list_flag_on_shows_market_core(monkeypatch, capsys) -> None:
    _strip_feature_env(monkeypatch)
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()
    main(["slots", "list"])
    out = capsys.readouterr().out
    assert "market.core" in out
    assert "tool" in out
    assert "tools=6" in out


def test_list_flag_on_json_payload(monkeypatch, capsys) -> None:
    _strip_feature_env(monkeypatch)
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()
    main(["slots", "list", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["slots"][0]["id"] == "market.core"
    assert payload["slots"][0]["type"] == "tool"
    assert payload["slots"][0]["tools"] == 6


def test_show_flag_off_disabled(monkeypatch, capsys) -> None:
    _strip_feature_env(monkeypatch)
    reset_settings()
    main(["slots", "show", "market.core"])
    assert "disabled" in capsys.readouterr().out


def test_show_flag_on_prints_manifest(monkeypatch, capsys) -> None:
    _strip_feature_env(monkeypatch)
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()
    main(["slots", "show", "market.core"])
    out = capsys.readouterr().out
    assert "id=market.core" in out
    assert "maturity=experimental" in out
    assert "query_stock" in out


def test_show_unknown_slot_exits_1(monkeypatch, capsys) -> None:
    _strip_feature_env(monkeypatch)
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()
    with pytest.raises(SystemExit) as exc:
        main(["slots", "show", "nope.slot"])
    assert exc.value.code == 1
