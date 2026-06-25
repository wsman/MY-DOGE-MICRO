import json
from pathlib import Path
import subprocess
import sys

import scripts.preflight_plan_closure_external as preflight_module
from scripts.preflight_plan_closure_external import build_preflight
from scripts.prepare_plan_closure_handoff import prepare_handoff_workspace


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json"
GOLD_CASES = ROOT / "tests" / "eval" / "gold_cases.json"


def test_preflight_plan_closure_external_reports_pending_external_inputs(monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.delenv("DOGE_LIVE_KIMI_AGENT_SDK", raising=False)

    payload = build_preflight(manifest_path=MANIFEST)

    assert payload["schema"] == "doge.plan_closure_external_preflight.v1"
    assert payload["result"] == "pending_external_inputs"
    assert payload["infrastructure_ready"] is True
    assert payload["external_inputs_ready"] is False
    assert payload["secret_values_redacted"] is True
    assert payload["closure_gate"]["summary"]["open"] == 5
    assert payload["closure_gate"]["summary"]["passed"] == 1
    assert payload["closure_gate"]["production_ready_false"] is True
    assert payload["closure_gate"]["stable_declaration_forbidden"] is True
    assert any("MOONSHOT_API_KEY" in blocker for blocker in payload["external_blockers"])
    assert "secret-value" not in json.dumps(payload)


def test_preflight_plan_closure_external_accepts_valid_handoff_workspace(tmp_path, monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    workspace = tmp_path / "handoff"
    prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)

    payload = build_preflight(manifest_path=MANIFEST, handoff_workspace=workspace)

    assert payload["infrastructure_ready"] is True
    assert _norm(payload["handoff_workspace"]) == _norm(str(workspace))
    assert not any(error.startswith("handoff:") for error in payload["infrastructure_errors"])
    assert any("workspace draft input not ready" in blocker for blocker in payload["external_blockers"])


def test_preflight_plan_closure_external_accepts_filled_handoff_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("DOGE_LIVE_KIMI", "1")
    monkeypatch.setenv("MOONSHOT_API_KEY", "secret-value")
    monkeypatch.setenv("DOGE_LIVE_KIMI_AGENT_SDK", "1")
    monkeypatch.setenv("KIMI_FILES_API_CAPABLE", "1")
    monkeypatch.setattr(
        preflight_module.importlib.util,
        "find_spec",
        lambda name: object() if name == "kimi_agent_sdk" else None,
    )
    workspace = tmp_path / "handoff"
    handoff = prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    _mark_all_draft_inputs_filled(handoff)

    payload = build_preflight(
        manifest_path=MANIFEST,
        handoff_workspace=workspace,
        require_external_inputs=True,
    )

    assert payload["result"] == "ready"
    assert payload["external_inputs_ready"] is True
    assert payload["infrastructure_ready"] is True
    assert payload["external_blockers"] == []
    assert "secret-value" not in json.dumps(payload)


def test_preflight_plan_closure_external_can_check_one_task(tmp_path, monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.delenv("DOGE_LIVE_KIMI_AGENT_SDK", raising=False)
    workspace = tmp_path / "handoff"
    handoff = prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    _mark_task_draft_inputs_filled(handoff, "S017-003")

    payload = build_preflight(
        manifest_path=MANIFEST,
        handoff_workspace=workspace,
        require_external_inputs=True,
        task_ids={"S017-003"},
    )

    assert payload["result"] == "ready"
    assert payload["requested_task_ids"] == ["S017-003"]
    assert [task["id"] for task in payload["tasks"]] == ["S017-003"]
    assert payload["external_blockers"] == []
    assert "MOONSHOT_API_KEY" not in json.dumps(payload["external_blockers"])


def test_preflight_plan_closure_external_rejects_invalid_filled_draft(tmp_path, monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    workspace = tmp_path / "handoff"
    handoff = prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    provider_task = next(task for task in handoff["tasks"] if task["id"] == "S017-003")
    provider_draft = ROOT / Path(provider_task["prepared_inputs"][0]["prepared_input"])
    provider_draft.write_text(json.dumps({"status": "operator-filled"}), encoding="utf-8")

    payload = build_preflight(
        manifest_path=MANIFEST,
        handoff_workspace=workspace,
        require_external_inputs=True,
        task_ids={"S017-003"},
    )

    assert payload["result"] == "failed"
    assert payload["external_inputs_ready"] is False
    assert any("invalid content" in blocker for blocker in payload["external_blockers"])
    check = payload["tasks"][0]["input_refs"][0]
    assert check["content_valid"] is False
    assert any("result must be" in error for error in check["content_errors"])


def test_preflight_plan_closure_external_rejects_residual_template_placeholder(tmp_path, monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    workspace = tmp_path / "handoff"
    handoff = prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    provider_task = next(task for task in handoff["tasks"] if task["id"] == "S017-003")
    provider_draft = ROOT / Path(provider_task["prepared_inputs"][0]["prepared_input"])
    payload = json.loads(provider_draft.read_text(encoding="utf-8"))
    payload["result"] = "approved"
    payload["approved_at"] = "2030-01-02T00:00:00Z"
    payload["operator"] = {"role": "product-owner", "initials": "PO"}
    payload["redaction_review"]["repository_storage_approved"] = True
    for decision in payload["decisions"].values():
        decision["decision_status"] = "approved"
        decision["notes"] = "Approved by operator fixture for preflight test."
    provider_draft.write_text(json.dumps(payload), encoding="utf-8")

    payload = build_preflight(
        manifest_path=MANIFEST,
        handoff_workspace=workspace,
        require_external_inputs=True,
        task_ids={"S017-003"},
    )

    assert payload["result"] == "failed"
    assert payload["external_inputs_ready"] is False
    assert any("unresolved placeholder" in blocker for blocker in payload["external_blockers"])
    check = payload["tasks"][0]["input_refs"][0]
    assert any("draft input contains unresolved placeholder: S017-003-TEMPLATE" in error for error in check["content_errors"])


def test_preflight_plan_closure_external_rejects_secret_shaped_draft_value(tmp_path, monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    workspace = tmp_path / "handoff"
    handoff = prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    _mark_task_draft_inputs_filled(handoff, "S017-003")
    provider_task = next(task for task in handoff["tasks"] if task["id"] == "S017-003")
    provider_draft = ROOT / Path(provider_task["prepared_inputs"][0]["prepared_input"])
    payload = json.loads(provider_draft.read_text(encoding="utf-8"))
    payload["decisions"]["financial_statements"]["notes"] = "MOONSHOT_API_KEY=sk-live-secret-value"
    provider_draft.write_text(json.dumps(payload), encoding="utf-8")

    payload = build_preflight(
        manifest_path=MANIFEST,
        handoff_workspace=workspace,
        require_external_inputs=True,
        task_ids={"S017-003"},
    )

    assert payload["result"] == "failed"
    assert any("unredacted secret assignment" in blocker for blocker in payload["external_blockers"])
    check = payload["tasks"][0]["input_refs"][0]
    assert any("draft input contains provider-style API key" in error for error in check["content_errors"])
    assert "sk-live-secret-value" not in json.dumps(payload)


def test_preflight_plan_closure_external_rejects_incomplete_provider_decision_details(tmp_path, monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    workspace = tmp_path / "handoff"
    handoff = prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    _mark_task_draft_inputs_filled(handoff, "S017-003")
    provider_task = next(task for task in handoff["tasks"] if task["id"] == "S017-003")
    provider_draft = ROOT / Path(provider_task["prepared_inputs"][0]["prepared_input"])
    payload = json.loads(provider_draft.read_text(encoding="utf-8"))
    payload["decisions"].pop("risk_factors")
    payload["decisions"]["financial_statements"]["decision_status"] = "needs_revision"
    payload["decisions"]["announcements"]["license_scope"] = "pending"
    provider_draft.write_text(json.dumps(payload), encoding="utf-8")

    payload = build_preflight(
        manifest_path=MANIFEST,
        handoff_workspace=workspace,
        require_external_inputs=True,
        task_ids={"S017-003"},
    )

    assert payload["result"] == "failed"
    check = payload["tasks"][0]["input_refs"][0]
    assert any("missing decisions: risk_factors" in error for error in check["content_errors"])
    assert any("financial_statements: approved draft requires decision_status=approved" in error for error in check["content_errors"])
    assert any("announcements.license_scope must be filled and not pending/template text" in error for error in check["content_errors"])


def test_preflight_plan_closure_external_rejects_missing_provider_redaction_flags(tmp_path, monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    workspace = tmp_path / "handoff"
    handoff = prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    _mark_task_draft_inputs_filled(handoff, "S017-003")
    provider_task = next(task for task in handoff["tasks"] if task["id"] == "S017-003")
    provider_draft = ROOT / Path(provider_task["prepared_inputs"][0]["prepared_input"])
    payload = json.loads(provider_draft.read_text(encoding="utf-8"))
    payload["redaction_review"].pop("contains_proprietary_data")
    provider_draft.write_text(json.dumps(payload), encoding="utf-8")

    payload = build_preflight(
        manifest_path=MANIFEST,
        handoff_workspace=workspace,
        require_external_inputs=True,
        task_ids={"S017-003"},
    )

    assert payload["result"] == "failed"
    check = payload["tasks"][0]["input_refs"][0]
    assert any("redaction_review.contains_proprietary_data must be false" in error for error in check["content_errors"])


def test_preflight_plan_closure_external_rejects_incomplete_sdk_release_details(tmp_path, monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    workspace = tmp_path / "handoff"
    handoff = prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    _mark_task_draft_inputs_filled(handoff, "S017-007")
    sdk_task = next(task for task in handoff["tasks"] if task["id"] == "S017-007")
    sdk_draft = ROOT / Path(sdk_task["prepared_inputs"][0]["prepared_input"])
    payload = json.loads(sdk_draft.read_text(encoding="utf-8"))
    payload["security_review"]["redaction_behavior_documented"] = False
    payload["packages"]["typescript"]["registry_consumer_smoke"] = "pending"
    payload["packages"]["python"]["decision_status"] = "needs_revision"
    sdk_draft.write_text(json.dumps(payload), encoding="utf-8")

    payload = build_preflight(
        manifest_path=MANIFEST,
        handoff_workspace=workspace,
        require_external_inputs=True,
        task_ids={"S017-007"},
    )

    assert payload["result"] == "failed"
    check = payload["tasks"][0]["input_refs"][0]
    assert any("approved draft requires security_review.redaction_behavior_documented=true" in error for error in check["content_errors"])
    assert any("typescript.registry_consumer_smoke must be filled and not pending/template text" in error for error in check["content_errors"])
    assert any("python: approved draft requires decision_status=approved" in error for error in check["content_errors"])


def test_preflight_plan_closure_external_rejects_missing_sdk_redaction_flags(tmp_path, monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    workspace = tmp_path / "handoff"
    handoff = prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    _mark_task_draft_inputs_filled(handoff, "S017-007")
    sdk_task = next(task for task in handoff["tasks"] if task["id"] == "S017-007")
    sdk_draft = ROOT / Path(sdk_task["prepared_inputs"][0]["prepared_input"])
    payload = json.loads(sdk_draft.read_text(encoding="utf-8"))
    payload["security_review"].pop("contains_credentials")
    sdk_draft.write_text(json.dumps(payload), encoding="utf-8")

    payload = build_preflight(
        manifest_path=MANIFEST,
        handoff_workspace=workspace,
        require_external_inputs=True,
        task_ids={"S017-007"},
    )

    assert payload["result"] == "failed"
    check = payload["tasks"][0]["input_refs"][0]
    assert any("security_review.contains_credentials must be false" in error for error in check["content_errors"])


def test_preflight_plan_closure_external_rejects_incomplete_enterprise_observation_details(tmp_path, monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    workspace = tmp_path / "handoff"
    handoff = prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    _mark_task_draft_inputs_filled(handoff, "AUTH-prod")
    task = next(task for task in handoff["tasks"] if task["id"] == "AUTH-prod")
    draft = ROOT / Path(task["prepared_inputs"][0]["prepared_input"])
    payload = json.loads(draft.read_text(encoding="utf-8"))
    payload["checks"].pop("siem_worm_export")
    payload["checks"]["live_idp_jwks"]["status"] = "blocked"
    payload["checks"]["live_idp_jwks"]["evidence_ref"] = "operator-secure-store://replace/live_idp_jwks"
    payload["redaction_review"]["contains_raw_subjects"] = True
    draft.write_text(json.dumps(payload), encoding="utf-8")

    payload = build_preflight(
        manifest_path=MANIFEST,
        handoff_workspace=workspace,
        require_external_inputs=True,
        task_ids={"AUTH-prod"},
    )

    assert payload["result"] == "failed"
    check = payload["tasks"][0]["input_refs"][0]
    assert any("missing checks: siem_worm_export" in error for error in check["content_errors"])
    assert any("live_idp_jwks: passed draft requires status=passed" in error for error in check["content_errors"])
    assert any("live_idp_jwks.evidence_ref must be filled and not pending/template text" in error for error in check["content_errors"])
    assert any("redaction_review.contains_raw_subjects must be false" in error for error in check["content_errors"])


def test_preflight_plan_closure_external_rejects_missing_enterprise_redaction_flags(tmp_path, monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    workspace = tmp_path / "handoff"
    handoff = prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    _mark_task_draft_inputs_filled(handoff, "AUTH-prod")
    task = next(task for task in handoff["tasks"] if task["id"] == "AUTH-prod")
    draft = ROOT / Path(task["prepared_inputs"][0]["prepared_input"])
    payload = json.loads(draft.read_text(encoding="utf-8"))
    payload["redaction_review"].pop("contains_credentials")
    draft.write_text(json.dumps(payload), encoding="utf-8")

    payload = build_preflight(
        manifest_path=MANIFEST,
        handoff_workspace=workspace,
        require_external_inputs=True,
        task_ids={"AUTH-prod"},
    )

    assert payload["result"] == "failed"
    check = payload["tasks"][0]["input_refs"][0]
    assert any("redaction_review.contains_credentials must be false" in error for error in check["content_errors"])


def test_preflight_plan_closure_external_rejects_incomplete_screen_reader_observation_details(tmp_path, monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    workspace = tmp_path / "handoff"
    handoff = prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    _mark_task_draft_inputs_filled(handoff, "S017-006")
    task = next(task for task in handoff["tasks"] if task["id"] == "S017-006")
    draft = ROOT / Path(task["prepared_inputs"][0]["prepared_input"])
    payload = json.loads(draft.read_text(encoding="utf-8"))
    payload["environment"]["screen_reader_version"] = ""
    payload["checks"].pop("sr_no_keyboard_trap")
    payload["checks"]["sr_keyboard_primary_controls"]["status"] = "failed"
    payload["redaction_review"]["contains_sensitive_documents"] = True
    draft.write_text(json.dumps(payload), encoding="utf-8")

    payload = build_preflight(
        manifest_path=MANIFEST,
        handoff_workspace=workspace,
        require_external_inputs=True,
        task_ids={"S017-006"},
    )

    assert payload["result"] == "failed"
    check = payload["tasks"][0]["input_refs"][0]
    assert any("environment.screen_reader_version must be filled" in error for error in check["content_errors"])
    assert any("missing checks: sr_no_keyboard_trap" in error for error in check["content_errors"])
    assert any("sr_keyboard_primary_controls: passed draft requires status=passed" in error for error in check["content_errors"])
    assert any("redaction_review.contains_sensitive_documents must be false" in error for error in check["content_errors"])


def test_preflight_plan_closure_external_rejects_missing_screen_reader_redaction_flags(tmp_path, monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    workspace = tmp_path / "handoff"
    handoff = prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    _mark_task_draft_inputs_filled(handoff, "S017-006")
    task = next(task for task in handoff["tasks"] if task["id"] == "S017-006")
    draft = ROOT / Path(task["prepared_inputs"][0]["prepared_input"])
    payload = json.loads(draft.read_text(encoding="utf-8"))
    payload["redaction_review"].pop("contains_secrets")
    draft.write_text(json.dumps(payload), encoding="utf-8")

    payload = build_preflight(
        manifest_path=MANIFEST,
        handoff_workspace=workspace,
        require_external_inputs=True,
        task_ids={"S017-006"},
    )

    assert payload["result"] == "failed"
    check = payload["tasks"][0]["input_refs"][0]
    assert any("redaction_review.contains_secrets must be false" in error for error in check["content_errors"])


def test_preflight_plan_closure_external_rejects_incomplete_analyst_observation_set(tmp_path, monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    workspace = tmp_path / "handoff"
    handoff = prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    _mark_task_draft_inputs_filled(handoff, "W3-live")
    task = next(task for task in handoff["tasks"] if task["id"] == "W3-live")
    observation_input = next(
        item
        for item in task["prepared_inputs"]
        if Path(item["source_template"]).name.startswith("live-kimi-observations-")
    )
    observation_path = ROOT / Path(observation_input["prepared_input"])
    payload = json.loads(observation_path.read_text(encoding="utf-8"))
    removed_case = _gold_cases()[0]["id"]
    payload["observations"].pop(removed_case)
    observation_path.write_text(json.dumps(payload), encoding="utf-8")

    payload = build_preflight(
        manifest_path=MANIFEST,
        handoff_workspace=workspace,
        require_external_inputs=True,
        task_ids={"W3-live"},
    )

    assert payload["result"] == "failed"
    assert any("observations missing gold case ids" in blocker for blocker in payload["external_blockers"])
    checks = [check for task in payload["tasks"] for check in task["input_refs"]]
    assert any(
        f"observations missing gold case ids: {removed_case}" in error
        for check in checks
        for error in check["content_errors"]
    )


def test_preflight_plan_closure_external_rejects_incomplete_analyst_observation_details(tmp_path, monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    workspace = tmp_path / "handoff"
    handoff = prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    _mark_task_draft_inputs_filled(handoff, "W3-live")
    task = next(task for task in handoff["tasks"] if task["id"] == "W3-live")
    observation_input = next(
        item
        for item in task["prepared_inputs"]
        if Path(item["source_template"]).name.startswith("live-kimi-observations-")
    )
    observation_path = ROOT / Path(observation_input["prepared_input"])
    payload = json.loads(observation_path.read_text(encoding="utf-8"))
    target_case = next(case for case in _gold_cases() if case.get("expected_numbers") and case.get("expected_citations"))
    case_id = target_case["id"]
    payload["observations"][case_id]["cited_evidence_ids"] = "not-a-list"
    payload["observations"][case_id]["numbers"].pop(target_case["expected_numbers"][0]["metric"])
    payload["observations"][case_id]["usage"] = {"cost_usd": 0.01}
    payload["observations"][case_id]["run_id"] = "raw-run-id"
    observation_path.write_text(json.dumps(payload), encoding="utf-8")

    payload = build_preflight(
        manifest_path=MANIFEST,
        handoff_workspace=workspace,
        require_external_inputs=True,
        task_ids={"W3-live"},
    )

    assert payload["result"] == "failed"
    checks = [check for task in payload["tasks"] for check in task["input_refs"]]
    assert any(
        f"observations.{case_id}.cited_evidence_ids must be a list of strings" in error
        for check in checks
        for error in check["content_errors"]
    )
    assert any(
        f"observations.{case_id}.numbers.{target_case['expected_numbers'][0]['metric']} must be numeric" in error
        for check in checks
        for error in check["content_errors"]
    )
    assert any(
        f"observations.{case_id}.usage.latency_ms must be a positive number" in error
        for check in checks
        for error in check["content_errors"]
    )
    assert any(
        f"observations.{case_id}.run_id must not be recorded" in error
        for check in checks
        for error in check["content_errors"]
    )


def test_preflight_plan_closure_external_rejects_incomplete_trend_history_details(tmp_path, monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    workspace = tmp_path / "handoff"
    handoff = prepare_handoff_workspace(manifest_path=MANIFEST, date="2030-01-02", output_dir=workspace)
    _mark_task_draft_inputs_filled(handoff, "W3-live")
    task = next(task for task in handoff["tasks"] if task["id"] == "W3-live")
    trend_input = next(
        item
        for item in task["prepared_inputs"]
        if Path(item["source_template"]).name.startswith("trend-history-")
    )
    trend_path = ROOT / Path(trend_input["prepared_input"])
    trend_path.write_text(
        json.dumps(
            {
                "status": "approved",
                "observed_at": "not-a-date",
                "run_id": "raw-run-id",
                "profiles": ["financial_research"],
                "case_count": len(_gold_cases()) - 1,
                "metrics": {"retrieval_recall": 1.0},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = build_preflight(
        manifest_path=MANIFEST,
        handoff_workspace=workspace,
        require_external_inputs=True,
        task_ids={"W3-live"},
    )

    assert payload["result"] == "failed"
    checks = [check for task in payload["tasks"] for check in task["input_refs"]]
    assert any("line 1: status must be passed or failed" in error for check in checks for error in check["content_errors"])
    assert any("line 1: observed_at must be ISO-8601" in error for check in checks for error in check["content_errors"])
    assert any("line 1: benchmark_run_id_hash must be a sha256: redacted hash" in error for check in checks for error in check["content_errors"])
    assert any("line 1: run_id must not be recorded" in error for check in checks for error in check["content_errors"])
    assert any("line 1: profiles must include financial_research and vision_analysis" in error for check in checks for error in check["content_errors"])
    assert any("line 1: case_count must match gold case count" in error for check in checks for error in check["content_errors"])
    assert any("line 1: metrics.citation_precision must be numeric" in error for check in checks for error in check["content_errors"])


def test_preflight_plan_closure_external_rejects_unknown_task_id():
    payload = build_preflight(manifest_path=MANIFEST, task_ids={"S999-404"})

    assert payload["result"] == "failed"
    assert any("unknown task id: S999-404" in error for error in payload["infrastructure_errors"])


def test_preflight_plan_closure_external_cli_require_external_inputs_fails_without_env(monkeypatch):
    monkeypatch.delenv("DOGE_LIVE_KIMI", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    script = ROOT / "scripts" / "preflight_plan_closure_external.py"

    result = subprocess.run(
        [sys.executable, str(script), "--manifest", str(MANIFEST), "--require-external-inputs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["result"] == "failed"
    assert payload["infrastructure_ready"] is True
    assert payload["external_inputs_ready"] is False


def test_preflight_plan_closure_external_cli_does_not_print_secret_env(monkeypatch):
    monkeypatch.setenv("DOGE_LIVE_KIMI", "1")
    monkeypatch.setenv("MOONSHOT_API_KEY", "secret-value")
    script = ROOT / "scripts" / "preflight_plan_closure_external.py"

    result = subprocess.run(
        [sys.executable, str(script), "--manifest", str(MANIFEST)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "secret-value" not in result.stdout


def _mark_all_draft_inputs_filled(handoff: dict) -> None:
    for task in handoff["tasks"]:
        for prepared in task["prepared_inputs"]:
            _write_valid_draft(prepared)


def _mark_task_draft_inputs_filled(handoff: dict, task_id: str) -> None:
    for task in handoff["tasks"]:
        if task["id"] != task_id:
            continue
        for prepared in task["prepared_inputs"]:
            _write_valid_draft(prepared)


def _write_valid_draft(prepared: dict) -> None:
    path = ROOT / Path(prepared["prepared_input"])
    template_name = Path(prepared["source_template"]).name
    if template_name.startswith("provider-decisions-"):
        payload = json.loads((ROOT / Path(prepared["source_template"])).read_text(encoding="utf-8"))
        payload["result"] = "approved"
        payload["approved_at"] = "2030-01-02T00:00:00Z"
        payload["issue_refs"] = []
        payload["operator"] = {"role": "product-owner", "initials": "PO"}
        payload["redaction_review"]["repository_storage_approved"] = True
        for decision in payload["decisions"].values():
            decision["decision_status"] = "approved"
            decision["approved_provider"] = "operator-approved-provider"
            decision["license_scope"] = "approved internal research fixture scope"
            decision["fixture_storage_policy"] = "synthetic fixtures only in repository; provider-derived fixtures in approved secure storage"
            decision["freshness_requirement"] = "daily or provider-native latest filing timestamp"
            decision["provenance_requirement"] = "provider id, source document id, as-of timestamp, and retrieval timestamp"
            decision["notes"] = "Approved by operator fixture for preflight test."
        path.write_text(json.dumps(payload), encoding="utf-8")
        return
    if template_name.startswith("sdk-release-decisions-"):
        payload = json.loads((ROOT / Path(prepared["source_template"])).read_text(encoding="utf-8"))
        payload["result"] = "approved"
        payload["approved_at"] = "2030-01-02T00:00:00Z"
        payload["issue_refs"] = []
        payload["release_manager"] = {"role": "release-manager", "initials": "RM"}
        payload["security_review"] = {
            "no_credentials_in_package_config": True,
            "typescript_sources_excluded_from_tarball": True,
            "redaction_behavior_documented": True,
            "contains_credentials": False,
        }
        for package in payload["packages"].values():
            package["decision_status"] = "approved"
            package["registry_target"] = "test-registry"
            package["package_name_ownership"] = "verified"
            package["version_policy"] = "semver"
            package["changelog_policy"] = "required"
            package["registry_consumer_smoke"] = "passed"
            package["notes"] = "Approved by release manager fixture for preflight test."
        path.write_text(json.dumps(payload), encoding="utf-8")
        return
    if template_name.startswith("enterprise-production-observations-"):
        payload = json.loads((ROOT / Path(prepared["source_template"])).read_text(encoding="utf-8"))
        payload["result"] = "passed"
        payload["executed_at"] = "2030-01-02T00:00:00Z"
        payload["operator"] = {"role": "platform-operator", "initials": "OPS"}
        payload["issue_refs"] = []
        for check in payload["checks"].values():
            check["status"] = "passed"
            check["evidence_ref"] = "operator-secure-store://redacted/preflight-test"
            check["issue_ref"] = ""
        path.write_text(json.dumps(payload), encoding="utf-8")
        return
    if template_name.startswith("screen-reader-observations-"):
        payload = json.loads((ROOT / Path(prepared["source_template"])).read_text(encoding="utf-8"))
        payload["result"] = "passed"
        payload["executed_at"] = "2030-01-02T00:00:00Z"
        payload["summary"] = "Manual screen-reader pass completed in preflight fixture."
        payload["operator"] = {"role": "accessibility-specialist", "initials": "QA"}
        payload["environment"] = {
            "platform": "Windows",
            "browser": "Chrome",
            "browser_version": "126.0.0",
            "screen_reader": "NVDA",
            "screen_reader_version": "2026.1",
            "web_url": "http://127.0.0.1:5173/research-agent",
            "doged_base_url": "http://127.0.0.1:8901",
            "live_kimi": False,
        }
        for check in payload["checks"].values():
            check["status"] = "passed"
            check["issue_ref"] = ""
            check["notes"] = "Passed in preflight fixture."
        payload["issues"] = []
        path.write_text(json.dumps(payload), encoding="utf-8")
        return
    if template_name.startswith("live-kimi-observations-"):
        observations = {
            case["id"]: {
                "retrieved_evidence_ids": [item["evidence_id"] for item in case.get("expected_citations", [])],
                "cited_evidence_ids": [item["evidence_id"] for item in case.get("expected_citations", [])],
                "numbers": {item["metric"]: item["value"] for item in case.get("expected_numbers", [])},
                "usage": {"cost_usd": 0.01, "latency_ms": 1000},
            }
            for case in _gold_cases()
        }
        path.write_text(json.dumps({"observations": observations}), encoding="utf-8")
        return
    if template_name.startswith("approved-thresholds-"):
        payload = json.loads((ROOT / Path(prepared["source_template"])).read_text(encoding="utf-8"))
        payload["latency_p95_ms_max"] = 29999.0
        path.write_text(json.dumps(payload), encoding="utf-8")
        return
    if template_name.startswith("material-manifest-"):
        path.write_text(json.dumps({"status": "approved", "case_count": len(_gold_cases())}), encoding="utf-8")
        return
    if template_name.startswith("label-manifest-"):
        cases = _gold_cases()
        path.write_text(
            json.dumps(
                {
                    "status": "approved",
                    "human_citation_labels": sum(len(case.get("expected_citations", [])) for case in cases),
                    "human_numerical_labels": sum(len(case.get("expected_numbers", [])) for case in cases),
                    "insufficient_evidence_labels": sum(
                        1
                        for case in cases
                        for claim in case.get("expected_claims", [])
                        if claim.get("expected_status") == "insufficient_evidence"
                    ),
                }
            ),
            encoding="utf-8",
        )
        return
    if template_name.startswith("trend-history-"):
        path.write_text(
            json.dumps(
                {
                    "status": "passed",
                    "observed_at": "2030-01-02T00:00:00Z",
                    "benchmark_run_id_hash": "sha256:preflight",
                    "profiles": ["financial_research", "vision_analysis"],
                    "case_count": len(_gold_cases()),
                    "metrics": {
                        "retrieval_recall": 1.0,
                        "retrieval_precision": 1.0,
                        "citation_precision": 1.0,
                        "numerical_consistency": 1.0,
                        "usage_cost_record_coverage": 1.0,
                        "latency_p95_ms": 1000.0,
                        "cost_usd_p95": 0.01,
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return
    path.write_text(json.dumps({"status": "operator-filled"}), encoding="utf-8")


def _gold_cases() -> list[dict]:
    return json.loads(GOLD_CASES.read_text(encoding="utf-8"))


def _norm(value: str) -> str:
    return value.replace("\\", "/")
