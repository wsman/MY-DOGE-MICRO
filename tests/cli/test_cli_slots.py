"""CLI tests for ``doge slots`` (ADR-0042)."""

from __future__ import annotations

import json

import pytest

from doge.config import reset_settings
from doge.bootstrap.runtime_factories.slots import clear_slot_bundle_activation
from doge.interfaces.cli.main import build_parser, main

_FEATURE_VARS = [
    "DOGE_FEATURE_RUN_SUMMARY_API",
    "DOGE_FEATURE_PLATFORM_OBJECTS",
    "DOGE_FEATURE_WORKFLOW_TEMPLATES",
    "DOGE_FEATURE_CAPABILITY_REGISTRY",
    "DOGE_FEATURE_RUNTIME_OUTBOX_PUBLISHER",
    "DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED",
    "DOGE_FEATURE_SLOT_PLATFORM",
    "DOGE_FEATURE_SLOT_GOVERNANCE",
    "DOGE_FEATURE_SLOT_WATCHER",
    "DOGE_FEATURE_SLOT_UI",
    "DOGE_FEATURE_SLOT_ENFORCEMENT",
    "DOGE_FEATURE_SLOT_LOADER",
    "DOGE_FEATURE_SLOT_INSTALL",
    "DOGE_SLOT_MANIFEST_DIRS",
    "DOGE_SLOT_INSTALL_DIR",
    "DOGE_SLOT_ENTERPRISE_ALLOWLIST",
    "DOGE_SLOT_TRUSTED_SIGNERS",
    "DOGE_SLOT_ALLOW_UNSIGNED_LOCAL",
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

    bundle_args = parser.parse_args(["slots", "bundle", "activate", "bundle.local_analyst", "--json"])
    assert bundle_args.slots_cmd == "bundle"
    assert bundle_args.bundle_cmd == "activate"
    assert bundle_args.bundle_id == "bundle.local_analyst"
    assert bundle_args.json is True

    install_args = parser.parse_args(["slots", "install", "slot.json", "--json"])
    assert install_args.slots_cmd == "install"
    assert install_args.source == "slot.json"
    assert install_args.json is True


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
    workflow = next(
        slot for slot in payload["slots"] if slot["id"] == "workflow.templates"
    )
    governance = next(
        slot for slot in payload["slots"] if slot["id"] == "governance.tool_policy"
    )
    watcher = next(
        slot for slot in payload["slots"] if slot["id"] == "watcher.runtime_events"
    )
    document = next(
        slot for slot in payload["slots"] if slot["id"] == "document.local_parser"
    )
    tdx = next(slot for slot in payload["slots"] if slot["id"] == "data.tdx")
    yfinance = next(slot for slot in payload["slots"] if slot["id"] == "data.yfinance")
    gateway = next(slot for slot in payload["slots"] if slot["id"] == "gateway.slots")
    eval_slot = next(slot for slot in payload["slots"] if slot["id"] == "eval.local_cases")
    ui_slot = next(slot for slot in payload["slots"] if slot["id"] == "ui.research_workspace")
    assert workflow["type"] == "workflow"
    assert workflow["status"] == "disabled"
    assert workflow["tools"] == 0
    assert governance["type"] == "governance"
    assert governance["status"] == "disabled"
    assert governance["tools"] == 0
    assert watcher["type"] == "watcher"
    assert watcher["status"] == "disabled"
    assert watcher["tools"] == 0
    assert document["type"] == "document"
    assert document["status"] == "resolved"
    assert document["tools"] == 0
    assert tdx["type"] == "data"
    assert tdx["status"] == "resolved"
    assert tdx["tools"] == 0
    assert yfinance["type"] == "data"
    assert yfinance["status"] == "resolved"
    assert yfinance["tools"] == 0
    assert gateway["type"] == "gateway"
    assert gateway["status"] == "resolved"
    assert gateway["tools"] == 0
    assert eval_slot["type"] == "eval"
    assert eval_slot["status"] == "resolved"
    assert eval_slot["tools"] == 0
    assert ui_slot["type"] == "ui"
    assert ui_slot["status"] == "disabled"
    assert ui_slot["tools"] == 0


def test_list_flag_on_json_marks_workflow_resolved_when_workflow_flag_on(
    monkeypatch, capsys
) -> None:
    _strip_feature_env(monkeypatch)
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_WORKFLOW_TEMPLATES", "1")
    reset_settings()
    main(["slots", "list", "--json"])
    payload = json.loads(capsys.readouterr().out)

    workflow = next(
        slot for slot in payload["slots"] if slot["id"] == "workflow.templates"
    )
    assert workflow["status"] == "resolved"


def test_list_flag_on_json_marks_governance_resolved_when_governance_flag_on(
    monkeypatch, capsys
) -> None:
    _strip_feature_env(monkeypatch)
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_SLOT_GOVERNANCE", "1")
    reset_settings()
    main(["slots", "list", "--json"])
    payload = json.loads(capsys.readouterr().out)

    governance = next(
        slot for slot in payload["slots"] if slot["id"] == "governance.tool_policy"
    )
    assert governance["status"] == "resolved"
    assert governance["type"] == "governance"


def test_list_flag_on_json_marks_watcher_resolved_when_watcher_flag_on(
    monkeypatch, capsys
) -> None:
    _strip_feature_env(monkeypatch)
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_SLOT_WATCHER", "1")
    reset_settings()
    main(["slots", "list", "--json"])
    payload = json.loads(capsys.readouterr().out)

    watcher = next(
        slot for slot in payload["slots"] if slot["id"] == "watcher.runtime_events"
    )
    assert watcher["status"] == "resolved"
    assert watcher["type"] == "watcher"


def test_list_flag_on_json_marks_ui_resolved_when_ui_flag_on(
    monkeypatch, capsys
) -> None:
    _strip_feature_env(monkeypatch)
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_SLOT_UI", "1")
    reset_settings()
    main(["slots", "list", "--json"])
    payload = json.loads(capsys.readouterr().out)

    ui_slot = next(
        slot for slot in payload["slots"] if slot["id"] == "ui.research_workspace"
    )
    assert ui_slot["status"] == "resolved"
    assert ui_slot["type"] == "ui"


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


def test_bundle_list_flag_on_json_payload(monkeypatch, capsys) -> None:
    _strip_feature_env(monkeypatch)
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()

    main(["slots", "bundle", "list", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["bundles"][0]["id"] == "bundle.local_analyst"
    assert payload["bundles"][0]["active"] is False


def test_bundle_activate_requires_slot_loader(monkeypatch, capsys) -> None:
    _strip_feature_env(monkeypatch)
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()

    with pytest.raises(SystemExit) as exc:
        main(["slots", "bundle", "activate", "bundle.local_analyst", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exc.value.code == 1
    assert payload == {"status": "disabled", "feature_flag": "DOGE_FEATURE_SLOT_LOADER"}


def test_bundle_activate_json_payload(monkeypatch, capsys) -> None:
    _strip_feature_env(monkeypatch)
    clear_slot_bundle_activation()
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_SLOT_LOADER", "1")
    reset_settings()

    try:
        main(["slots", "bundle", "activate", "bundle.daemon_operator", "--json"])
    finally:
        clear_slot_bundle_activation()
        monkeypatch.delenv("DOGE_FEATURE_SLOT_PLATFORM", raising=False)
        monkeypatch.delenv("DOGE_FEATURE_SLOT_LOADER", raising=False)
        reset_settings()

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "activated"
    assert payload["active_bundle_id"] == "bundle.daemon_operator"
    assert payload["bundle"]["active"] is True


def test_install_requires_slot_install(monkeypatch, capsys, tmp_path) -> None:
    _strip_feature_env(monkeypatch)
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_SLOT_LOADER", "1")
    reset_settings()

    with pytest.raises(SystemExit) as exc:
        main(["slots", "install", str(tmp_path / "slot.json"), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exc.value.code == 1
    assert payload == {"status": "disabled", "feature_flag": "DOGE_FEATURE_SLOT_INSTALL"}


def test_install_json_payload(monkeypatch, capsys, tmp_path) -> None:
    _strip_feature_env(monkeypatch)
    manifest = tmp_path / "slot.json"
    manifest.write_text(json.dumps(_manifest("local.cli")), encoding="utf-8")
    install_dir = tmp_path / "installed"
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    monkeypatch.setenv("DOGE_FEATURE_SLOT_LOADER", "1")
    monkeypatch.setenv("DOGE_FEATURE_SLOT_INSTALL", "1")
    monkeypatch.setenv("DOGE_SLOT_INSTALL_DIR", str(install_dir))
    reset_settings()

    try:
        main(["slots", "install", str(manifest), "--json"])
    finally:
        reset_settings()

    payload = json.loads(capsys.readouterr().out)
    assert payload["slot_id"] == "local.cli"
    assert payload["status"] == "installed"
    assert payload["signature"]["status"] == "missing"
    assert payload["warnings"] == ["unsigned local slot manifest"]
    assert (install_dir / "local_cli" / "slot.json").exists()


def _manifest(slot_id: str) -> dict:
    return {
        "schema_version": 1,
        "id": slot_id,
        "name": "Local CLI Preview",
        "version": "0.1.0",
        "type": "workflow",
        "owner": "doge.local",
        "maturity": "experimental",
        "description": "Local CLI manifest-only slot preview.",
        "entrypoint": "doge.local.preview",
        "provides": {"capabilities": ["local_preview"]},
        "feature_flags": ["slot_platform"],
    }
