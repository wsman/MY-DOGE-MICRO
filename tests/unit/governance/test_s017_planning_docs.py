import json
from collections import Counter
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_enterprise_auth_implementation_plan_records_required_choices():
    text = _read("docs/progress/enterprise-auth-implementation-plan.md")

    required = [
        "OIDC provider boundary",
        "Token validation library",
        "PyJWT[crypto]",
        "Tenant ACL persistence",
        "Approval/audit actor store",
        "SecretProvider",
        "AUTH-001",
        "AUTH-007",
        "X-Request-ID",
        "redact",
        "DOGE_ALLOW_REMOTE_BIND",
        "DOGE_CORS_ALLOW_ORIGINS",
        "DOGE_API_TLS_TERMINATION_REQUIRED",
        "production_ready",
        "enterprise-production-validation-template-2026-06-22.json",
        "build_enterprise_production_validation_evidence.py",
        "validate_enterprise_production_validation_evidence.py",
    ]

    for item in required:
        assert item in text


def test_enterprise_production_validation_template_is_ready_but_not_done():
    sprint = _read("production/sprint-status.yaml")
    sprint_plan = _read("production/sprints/sprint-017-external-validation-and-provider-hardening.md")
    maturity = _read("docs/progress/runtime-maturity.yaml")
    audit = _read("docs/progress/kimi-plan-completion-audit.md")
    template = json.loads(
        _read("production/qa/evidence/enterprise/enterprise-production-validation-template-2026-06-22.json")
    )

    body = re.search(r"- id: S017-004(?P<body>.*?)(?=\n\n      - id: S017-005)", sprint, re.S).group("body")
    assert "status: done" in body
    assert "enterprise production validation template/builder/validator" in body
    assert "operator-approved environment remain open" in body
    assert template["schema"] == "doge.enterprise_production_validation.v1"
    assert template["story_id"] == "S017-004"
    assert template["result"] == "not_run"
    assert {item["id"] for item in template["checks"]} == {
        "live_idp_jwks",
        "production_secret_store_command",
        "siem_worm_export",
        "live_remote_bind_deployment",
        "production_data_isolation_review",
    }
    assert all(item["status"] == "not_run" for item in template["checks"])
    assert template["redaction_review"]["contains_credentials"] is False
    for text in [sprint_plan, maturity, audit]:
        assert "enterprise-production-validation-template-2026-06-22.json" in text
        assert "build_enterprise_production_validation_evidence.py" in text
        assert "validate_enterprise_production_validation_evidence.py" in text


def test_financial_provider_approval_packet_keeps_external_approval_pending():
    text = _read("docs/progress/financial-provider-approval-packet.md")
    normalized = " ".join(text.split())

    assert "Pending product/operator approval" in text
    assert "S017-003 is ready for review, not done" in text
    assert "financial-provider-approval-template-2026-06-22.json" in text
    assert "validate_financial_provider_approval_evidence.py" in text
    assert "build_financial_provider_approval_evidence.py" in text
    assert "compact operator decision JSON" in text
    assert "default validation requires completed approval evidence" in normalized
    for capability in [
        "Financial statements",
        "Company announcements",
        "Consensus estimates",
        "Industry classification",
        "Risk factors",
    ]:
        assert capability in text


def test_financial_provider_approval_template_is_ready_but_not_done():
    sprint = _read("production/sprint-status.yaml")
    sprint_plan = _read("production/sprints/sprint-017-external-validation-and-provider-hardening.md")
    maturity = _read("docs/progress/runtime-maturity.yaml")
    audit = _read("docs/progress/kimi-plan-completion-audit.md")
    template = json.loads(
        _read("production/qa/evidence/provider/financial-provider-approval-template-2026-06-22.json")
    )

    body = re.search(r"- id: S017-003(?P<body>.*?)(?=\n\n      - id: S017-004)", sprint, re.S).group("body")
    assert "status: review" in body
    assert "validate_financial_provider_approval_evidence.py" in body
    assert "Product/operator approval" in body
    assert template["schema"] == "doge.financial_provider_approval.v1"
    assert template["story_id"] == "S017-003"
    assert template["result"] == "not_run"
    assert {item["capability"] for item in template["decisions"]} == {
        "financial_statements",
        "announcements",
        "consensus",
        "industry_classification",
        "risk_factors",
    }
    assert all(item["decision_status"] == "not_decided" for item in template["decisions"])
    for text in [sprint_plan, maturity, audit]:
        assert "financial-provider-approval-template-2026-06-22.json" in text
        assert "validate_financial_provider_approval_evidence.py" in text
        assert "build_financial_provider_approval_evidence.py" in text


def test_kimi_live_smoke_readiness_is_review_not_done():
    sprint = _read("production/sprint-status.yaml")
    sprint_plan = _read("production/sprints/sprint-017-external-validation-and-provider-hardening.md")
    maturity = _read("docs/progress/runtime-maturity.yaml")
    audit = _read("docs/progress/kimi-plan-completion-audit.md")
    live_test = _read("tests/live/test_kimi_live_smoke.py")
    live_runner = _read("scripts/run_kimi_live_smoke.py")
    live_validator = _read("scripts/validate_kimi_live_smoke_evidence.py")
    live_validator_test = _read("tests/unit/qa/test_validate_kimi_live_smoke_evidence.py")
    evidence = json.loads(_read("production/qa/evidence/live/kimi-live-smoke-2026-06-22.json"))

    body = re.search(r"- id: S017-002(?P<body>.*?)(?=\n\n      - id: S017-003)", sprint, re.S).group("body")
    assert "status: review" in body
    assert "Ready for operator execution, not done" in body
    assert evidence["schema"] == "doge.kimi_live_smoke.v1"
    assert evidence["story_id"] == "S017-002"
    assert evidence["result"] == "blocked"
    assert evidence["blockers"] == ["DOGE_LIVE_KIMI=1", "MOONSHOT_API_KEY"]
    assert evidence["scenarios"] == []
    for text in [sprint_plan, maturity, audit]:
        assert "scripts/run_kimi_live_smoke.py" in text
        assert "scripts/validate_kimi_live_smoke_evidence.py" in text
        assert "Files cleanup" in text or "file-cleanup" in text or "cleanup confirmation" in text
    assert "validates only with `--allow-blocked`" in sprint_plan
    assert "S017_KIMI_TEXT_OK" in live_test
    assert "S017_AGENT_SDK_OK" in live_test
    assert "S016_" not in live_test
    assert "_capture_scenario" in live_runner
    assert "[REDACTED_FILE_ID]" in live_runner
    assert "[REDACTED_API_KEY]" in live_runner
    assert "evidence requires environment" in live_validator
    assert "files_upload: file.deleted must be true" in live_validator
    assert "usage summary is required for passed scenario" in live_validator
    assert "usage.reported must be true or false" in live_validator
    assert "test_passed_required_scenario_requires_usage_summary" in live_validator_test
    assert "test_usage_summary_rejects_unexpected_provider_payload_keys" in live_validator_test


def test_kimi_plan_completion_audit_preserves_non_production_posture():
    text = _read("docs/progress/kimi-plan-completion-audit.md")
    normalized = " ".join(text.split())

    assert "not yet provably complete" in normalized
    assert "production_ready` must remain `false" in text
    assert "stable_declaration` must remain" in text
    for external_item in ["S017-002", "S017-003", "W3-live", "AUTH-prod", "S017-006", "S017-007"]:
        assert external_item in text
    assert "analyst-benchmark-template-2026-06-22.json" in text
    assert "validate_analyst_benchmark_evidence.py" in text
    assert "scripts/validate_kimi_plan_completion_audit.py" in text
    assert "scripts/validate_governance_yaml_shape.py" in text
    assert "test_validate_governance_yaml_shape.py" in text


def test_fastapi_route_count_governance_syncs_to_s017_surface():
    api = _read("docs/API.md")
    cdd = _read("design/cdd/fastapi-service.md")
    architecture_registry = _read("docs/registry/architecture.yaml")
    entities_registry = _read("docs/registry/entities.yaml")
    tr_registry = _read("docs/architecture/tr-registry.yaml")
    traceability = _read("docs/architecture/architecture-traceability.md")
    adr_0007 = _read("docs/architecture/adr-0007-api-surface-and-cors.md")
    imported_state = _read("docs/imports/my-doge-micro/current-state-2026-06-21.md")

    route_rows = re.findall(
        r"^\|\s*\d+\s*\|\s*(GET|POST|PUT|DELETE|PATCH)\s*\|\s*`([^`]+)`",
        api,
        re.M,
    )
    entity_routes = re.findall(
        r"\n\s+- \{num: \d+, method: (GET|POST|PUT|DELETE|PATCH), path: \"([^\"]+)\"",
        entities_registry,
    )

    assert len(route_rows) == 58
    assert len(entity_routes) == 58
    assert set(entity_routes) == set(route_rows)
    for path in [
        "/v1/portfolios/import",
        "/v1/audit/events",
        "/v1/audit/events/export",
        "/v1/audit/events/retention",
        "/v1/enterprise/acl/grants",
    ]:
        assert path in api
        assert path in entities_registry
    for text in [
        api,
        cdd,
        architecture_registry,
        tr_registry,
        traceability,
        adr_0007,
        imported_state,
    ]:
        assert "58 product routes" in text
        assert "51 product routes" not in text
    assert "58 canonical product routes" in entities_registry
    assert "51 canonical product routes" not in entities_registry


def test_plan_closure_gate_aggregates_remaining_external_evidence():
    maturity = _read("docs/progress/runtime-maturity.yaml")
    audit = _read("docs/progress/kimi-plan-completion-audit.md")
    sprint_plan = _read("production/sprints/sprint-017-external-validation-and-provider-hardening.md")
    sprint = _read("production/sprint-status.yaml")
    runbook = _read("docs/progress/9b77f9c-external-closure-runbook.md")
    gate_script = _read("scripts/validate_plan_closure_gate.py")
    runbook_validator = _read("scripts/validate_plan_closure_runbook.py")
    manifest_exporter = _read("scripts/export_plan_closure_manifest.py")
    manifest_validator = _read("scripts/validate_plan_closure_manifest.py")
    audit_validator = _read("scripts/validate_kimi_plan_completion_audit.py")
    external_preflight = _read("scripts/preflight_plan_closure_external.py")
    handoff_preparer = _read("scripts/prepare_plan_closure_handoff.py")
    handoff_validator = _read("scripts/validate_plan_closure_handoff.py")
    yaml_shape_validator = _read("scripts/validate_governance_yaml_shape.py")
    placeholder_helper = _read("scripts/evidence_placeholders.py")
    redaction_helper = _read("scripts/evidence_redaction.py")
    analyst_builder = _read("scripts/build_analyst_benchmark_evidence.py")
    analyst_validator = _read("scripts/validate_analyst_benchmark_evidence.py")
    enterprise_builder = _read("scripts/build_enterprise_production_validation_evidence.py")
    enterprise_validator = _read("scripts/validate_enterprise_production_validation_evidence.py")
    provider_builder = _read("scripts/build_financial_provider_approval_evidence.py")
    provider_validator = _read("scripts/validate_financial_provider_approval_evidence.py")
    sdk_builder = _read("scripts/build_sdk_release_approval_evidence.py")
    sdk_validator = _read("scripts/validate_sdk_release_approval_evidence.py")
    screen_reader_builder = _read("scripts/build_screen_reader_evidence.py")
    screen_reader_validator = _read("scripts/validate_screen_reader_evidence.py")
    gate_test = _read("tests/unit/qa/test_validate_plan_closure_gate.py")
    runbook_test = _read("tests/unit/qa/test_validate_plan_closure_runbook.py")
    manifest_test = _read("tests/unit/qa/test_export_plan_closure_manifest.py")
    manifest_validator_test = _read("tests/unit/qa/test_validate_plan_closure_manifest.py")
    audit_validator_test = _read("tests/unit/qa/test_validate_kimi_plan_completion_audit.py")
    external_preflight_test = _read("tests/unit/qa/test_preflight_plan_closure_external.py")
    handoff_test = _read("tests/unit/qa/test_prepare_plan_closure_handoff.py")
    handoff_validator_test = _read("tests/unit/qa/test_validate_plan_closure_handoff.py")
    yaml_shape_validator_test = _read("tests/unit/qa/test_validate_governance_yaml_shape.py")
    placeholder_test = _read("tests/unit/qa/test_evidence_placeholders.py")
    redaction_test = _read("tests/unit/qa/test_evidence_redaction.py")
    input_template_test = _read("tests/unit/qa/test_plan_closure_input_templates.py")
    analyst_builder_test = _read("tests/unit/qa/test_build_analyst_benchmark_evidence.py")
    analyst_validator_test = _read("tests/unit/qa/test_validate_analyst_benchmark_evidence.py")
    enterprise_builder_test = _read("tests/unit/qa/test_build_enterprise_production_validation_evidence.py")
    enterprise_validator_test = _read("tests/unit/qa/test_validate_enterprise_production_validation_evidence.py")
    provider_builder_test = _read("tests/unit/qa/test_build_financial_provider_approval_evidence.py")
    provider_validator_test = _read("tests/unit/qa/test_validate_financial_provider_approval_evidence.py")
    sdk_builder_test = _read("tests/unit/qa/test_build_sdk_release_approval_evidence.py")
    sdk_validator_test = _read("tests/unit/qa/test_validate_sdk_release_approval_evidence.py")
    screen_reader_builder_test = _read("tests/unit/qa/test_build_screen_reader_evidence.py")
    screen_reader_validator_test = _read("tests/unit/qa/test_validate_screen_reader_evidence.py")
    manifest = json.loads(_read("production/qa/evidence/plan-closure/9b77f9c-external-closure-manifest.json"))

    for text in [maturity, audit, sprint_plan, sprint]:
        assert "validate_plan_closure_gate.py" in text
        assert "validate_plan_closure_runbook.py" in text
        assert "export_plan_closure_manifest.py" in text
        assert "validate_plan_closure_manifest.py" in text
        assert "validate_kimi_plan_completion_audit.py" in text
        assert "preflight_plan_closure_external.py" in text
        assert "prepare_plan_closure_handoff.py" in text
        assert "validate_plan_closure_handoff.py" in text
        assert "controlled open" in text
        assert "9b77f9c-external-closure-runbook.md" in text
        assert "9b77f9c-external-closure-manifest.json" in text
    assert "test_validate_plan_closure_gate.py" in maturity
    assert "test_validate_plan_closure_runbook.py" in maturity
    assert "test_export_plan_closure_manifest.py" in maturity
    assert "test_validate_plan_closure_manifest.py" in maturity
    assert "test_validate_kimi_plan_completion_audit.py" in maturity
    assert "test_preflight_plan_closure_external.py" in maturity
    assert "test_prepare_plan_closure_handoff.py" in maturity
    assert "test_validate_plan_closure_handoff.py" in maturity
    assert "scripts/validate_governance_yaml_shape.py" in maturity
    assert "test_validate_governance_yaml_shape.py" in maturity
    assert "scripts/evidence_placeholders.py" in maturity
    assert "test_evidence_placeholders.py" in maturity
    assert "scripts/evidence_redaction.py" in maturity
    assert "test_evidence_redaction.py" in maturity
    assert "evidence_placeholders.py" in sprint_plan
    assert "evidence_redaction.py" in sprint_plan
    assert "evidence_placeholders.py" in audit
    assert "workspace_command_plan" in maturity
    assert "source_plan_check" in maturity
    assert "passing_results" in maturity
    assert "strict mode" in sprint_plan
    assert "passing_results" in sprint_plan
    assert "required results" in sprint_plan
    assert "strict validation rejects" in audit
    assert "structurally valid failed/rejected/needs_revision evidence does not complete" in audit
    assert "next_action" in sprint_plan
    assert "strict_command" in sprint_plan
    assert "completed-evidence filename patterns" in sprint_plan
    assert "builder/runner handoff commands" in sprint_plan
    assert "source-plan fingerprints" in sprint_plan
    assert "source plan SHA-256" in sprint_plan
    assert "operator-commands.ps1" in sprint_plan
    assert "input template refs" in sprint_plan
    assert "Required Result" in runbook
    assert "export_plan_closure_manifest.py" in runbook
    assert "validate_plan_closure_manifest.py" in runbook
    assert "preflight_plan_closure_external.py" in runbook
    assert "prepare_plan_closure_handoff.py" in runbook
    assert "validate_plan_closure_handoff.py" in runbook
    assert "operator-commands.ps1" in runbook
    assert "workspace_command_plan" in runbook
    assert "build_analyst_benchmark_evidence.py" in runbook
    assert "build_enterprise_production_validation_evidence.py" in runbook
    assert "build_financial_provider_approval_evidence.py" in runbook
    assert "build_screen_reader_evidence.py" in runbook
    assert "build_sdk_release_approval_evidence.py" in runbook
    assert "stale handoff files" in runbook
    assert "source_plan_check" in runbook
    assert "source-plan fingerprint" in runbook
    assert "builder/runner handoff metadata" in runbook
    assert "input template references" in runbook

    for gate_id in ["S017-002", "S017-003", "W3-live", "AUTH-prod", "S017-006", "S017-007"]:
        assert gate_id in gate_script
        assert gate_id in runbook
    for evidence in [
        "kimi-live-smoke-2026-06-22.json",
        "financial-provider-approval-template-2026-06-22.json",
        "analyst-benchmark-template-2026-06-22.json",
        "enterprise-production-validation-template-2026-06-22.json",
        "research-agent-screen-reader-manual-template-2026-06-22.json",
        "sdk-release-approval-template-2026-06-22.json",
    ]:
        assert evidence in gate_script
        assert evidence in runbook
    for snippet in [
        "validate_plan_closure_gate.py --allow-open",
        "validate_plan_closure_gate.py",
        "DOGE_LIVE_KIMI",
        "MOONSHOT_API_KEY",
        "strict gate exits 0",
    ]:
        assert snippet in runbook
    assert "summary" in gate_test
    assert "open" in gate_test
    assert "passing_results" in gate_script
    assert "passing_results" in gate_test
    assert "from scripts.validate_plan_closure_gate import GATES" in runbook_validator
    assert "for gate in GATES" in runbook_validator
    assert "RUNBOOK" in runbook_validator
    assert "completed pattern" in runbook_validator
    assert "test_plan_closure_runbook_matches_gate_manifest" in runbook_test
    assert "build_manifest" in manifest_exporter
    assert "doge.plan_closure_execution_manifest.v1" in manifest_exporter
    assert "source_plan_check" in manifest_exporter
    assert "hashlib.sha256" in manifest_exporter
    assert "HANDOFFS" in manifest_exporter
    assert "build_or_run_command" in manifest_exporter
    assert "close_condition" in manifest_exporter
    assert "input_templates" in manifest_exporter
    assert "build_manifest" in manifest_validator
    assert "manifest does not match current closure gate" in manifest_validator
    assert "source_plan_check" in manifest_validator
    assert "mismatch:" in manifest_validator
    assert "validate_all(allow_open=True)" in audit_validator
    assert "test_kimi_plan_completion_audit_matches_closure_gate" in audit_validator_test
    assert "doge.plan_closure_external_preflight.v1" in external_preflight
    assert "require_external_inputs" in external_preflight
    assert "task_ids" in external_preflight
    assert "--task-id" in external_preflight
    assert "secret" in external_preflight
    assert "kimi_agent_sdk" in external_preflight
    assert "workspace_draft_input" in external_preflight
    assert "differs_from_template" in external_preflight
    assert "content_valid" in external_preflight
    assert "content_errors" in external_preflight
    assert "_draft_content_errors" in external_preflight
    assert "placeholder_errors" in external_preflight
    assert "secret_leak_errors" in external_preflight
    assert "draft input" in external_preflight
    assert "GOLD_CASES_PATH" in external_preflight
    assert "_live_observation_case_errors" in external_preflight
    assert "_live_observation_detail_errors" in external_preflight
    assert "validate_trend_history_jsonl" in external_preflight
    assert "validate_trend_history_jsonl" in analyst_builder
    assert "validate_trend_history_jsonl" in analyst_validator
    assert "_validate_local_trend_history_ref" in analyst_builder
    assert "_validate_local_trend_history_ref" in analyst_validator
    assert "run_id" in external_preflight
    assert "PROVIDER_APPROVAL_FIELDS" in external_preflight
    assert "SDK_SECURITY_APPROVAL_FIELDS" in external_preflight
    assert "ENTERPRISE_PRODUCTION_CHECK_IDS" in external_preflight
    assert "SCREEN_READER_CHECK_IDS" in external_preflight
    assert "_provider_decision_errors" in external_preflight
    assert "_sdk_release_decision_errors" in external_preflight
    assert "_enterprise_production_observation_errors" in external_preflight
    assert "_screen_reader_observation_errors" in external_preflight
    assert "_require_false(redaction.get(\"contains_credentials\")" in external_preflight
    assert "_require_false(security.get(\"contains_credentials\")" in external_preflight
    assert "_require_false(redaction.get(key), f\"redaction_review.{key}\"" in external_preflight
    assert "_require_false(redaction.get(\"contains_secrets\")" in external_preflight
    assert "edited drafts that still" in runbook
    assert "credential-shaped values" in runbook
    assert "approved provider, license scope, fixture storage, freshness, and provenance" in runbook
    assert "registry-backed consumer smoke" in runbook
    assert "five enterprise" in runbook
    assert "six manual observation checks" in runbook
    assert "retrieved and cited" in runbook
    assert "evidence id arrays" in runbook
    assert "usage cost/latency" in runbook
    assert "trend-history JSONL" in runbook
    assert "gold_cases.json" in runbook
    assert "prepare_handoff_workspace" in handoff_preparer
    assert "doge.plan_closure_handoff_workspace.v1" in handoff_preparer
    assert "Source plan SHA-256" in handoff_preparer
    assert "does_not_close_gates" in handoff_preparer
    assert "validate_kimi_plan_completion_audit.py" in handoff_preparer
    assert "copied_template_for_operator_edit" in handoff_preparer
    assert "workspace_command_plan" in handoff_preparer
    assert "operator-commands.ps1" in handoff_preparer
    assert "operator-checklist.md" in handoff_preparer
    assert "_render_operator_checklist" in handoff_preparer
    assert "_render_operator_commands" in handoff_preparer
    assert "_quote_powershell_paths" in handoff_preparer
    assert "Set-Location -LiteralPath $repoRoot" in handoff_preparer
    assert "$python = Join-Path $repoRoot" in handoff_preparer
    assert "Test-Path -LiteralPath $python" in handoff_preparer
    assert "[ValidateSet(" in handoff_preparer
    assert "$preflightArgs += @('--task-id', $TaskId)" in handoff_preparer
    assert "$RunFinalGate" in handoff_preparer
    assert "writes_completed_evidence_to_workspace" in handoff_preparer
    assert "validate_workspace" in handoff_validator
    assert "source_plan_check does not match manifest" in handoff_validator
    assert "completed-evidence-looking file" in handoff_validator
    assert "does_not_close_gates must be true" in handoff_validator
    assert "resolved_output_ref must not be inside handoff workspace" in handoff_validator
    assert "operator commands must run external preflight" in handoff_validator
    assert "operator commands must include the strict closure gate" in handoff_validator
    assert "operator commands must validate the completion audit before the strict gate" in handoff_validator
    assert "completion audit before the strict closure gate" in handoff_validator
    assert "_first_script_index" in handoff_validator
    assert "operator checklist must include quick start steps" in handoff_validator
    assert "operator checklist must reject template-as-evidence closure" in handoff_validator
    assert "operator commands must switch to the repository root" in handoff_validator
    assert "operator commands must define the Python interpreter path" in handoff_validator
    assert "operator commands must support task-scoped execution" in handoff_validator
    assert "Redaction and security-review flags must be explicit `false`" in handoff_preparer
    assert "operator checklist must require explicit false redaction/security-review flags" in handoff_validator
    assert "score_observations" in analyst_builder
    assert "Enterprise production validation failed" in enterprise_builder
    assert "provider approval result is" in provider_builder
    assert "SDK release approval result is" in sdk_builder
    assert "compact operator observations" in screen_reader_builder
    assert '_required_bool(review, "contains_credentials")' in provider_builder
    assert '_required_bool(review, "contains_credentials")' in sdk_builder
    assert "REQUIRED_REDACTION_FLAGS" in enterprise_builder
    assert "contains_proprietary_customer_data" in enterprise_builder
    assert "REQUIRED_REDACTION_FLAGS" in screen_reader_builder
    assert "contains_sensitive_documents" in screen_reader_builder
    assert "_require_timestamp(payload.get(\"created_at\"), \"created_at\", errors)" in screen_reader_validator
    assert "_require_false(redaction.get(\"contains_credentials\")" in provider_validator
    assert "_require_false(security.get(\"contains_credentials\")" in sdk_validator
    assert "_require_false(redaction.get(key), f\"redaction_review.{key}\"" in enterprise_validator
    assert "_require_false(redaction.get(\"contains_secrets\")" in screen_reader_validator
    assert "redaction_review.contains_sensitive_documents" in screen_reader_validator
    assert "failed evidence" in sprint_plan
    assert "failed evidence" in sprint_plan
    assert "issue references" in sprint_plan
    assert "test_build_plan_closure_manifest_from_gate_output" in manifest_test
    assert "test_plan_closure_manifest_matches_current_gate" in manifest_validator_test
    assert "test_plan_closure_manifest_rejects_stale_source_plan_hash" in manifest_validator_test
    assert "test_preflight_plan_closure_external_reports_pending_external_inputs" in external_preflight_test
    assert "test_preflight_plan_closure_external_accepts_filled_handoff_workspace" in external_preflight_test
    assert "test_preflight_plan_closure_external_can_check_one_task" in external_preflight_test
    assert "test_preflight_plan_closure_external_rejects_invalid_filled_draft" in external_preflight_test
    assert "test_preflight_plan_closure_external_rejects_residual_template_placeholder" in external_preflight_test
    assert "test_preflight_plan_closure_external_rejects_incomplete_provider_decision_details" in external_preflight_test
    assert "test_preflight_plan_closure_external_rejects_missing_provider_redaction_flags" in external_preflight_test
    assert "test_preflight_plan_closure_external_rejects_incomplete_sdk_release_details" in external_preflight_test
    assert "test_preflight_plan_closure_external_rejects_missing_sdk_redaction_flags" in external_preflight_test
    assert "test_preflight_plan_closure_external_rejects_incomplete_enterprise_observation_details" in external_preflight_test
    assert "test_preflight_plan_closure_external_rejects_missing_enterprise_redaction_flags" in external_preflight_test
    assert "test_preflight_plan_closure_external_rejects_incomplete_screen_reader_observation_details" in external_preflight_test
    assert "test_preflight_plan_closure_external_rejects_missing_screen_reader_redaction_flags" in external_preflight_test
    assert "test_preflight_plan_closure_external_rejects_incomplete_analyst_observation_set" in external_preflight_test
    assert "test_preflight_plan_closure_external_rejects_incomplete_analyst_observation_details" in external_preflight_test
    assert "test_preflight_plan_closure_external_rejects_incomplete_trend_history_details" in external_preflight_test
    assert "test_build_analyst_benchmark_evidence_rejects_invalid_trend_history" in analyst_builder_test
    assert "test_local_trend_history_ref_must_be_scoreable_and_redacted" in analyst_validator_test
    assert "test_prepare_plan_closure_handoff_copies_draft_inputs_without_closing_gates" in handoff_test
    assert "test_prepare_plan_closure_handoff_quotes_operator_paths_with_spaces" in handoff_test
    assert "operator-commands.ps1" in handoff_test
    assert "operator-checklist.md" in handoff_test
    assert "Redaction and security-review flags must be explicit `false`" in handoff_test
    assert "source_plan_check" in handoff_test
    assert "test_validate_plan_closure_handoff_accepts_fresh_workspace" in handoff_validator_test
    assert "test_validate_plan_closure_handoff_rejects_stale_source_plan_check" in handoff_validator_test
    assert "test_validate_plan_closure_handoff_rejects_command_plan_output_inside_workspace" in handoff_validator_test
    assert "test_validate_plan_closure_handoff_rejects_missing_operator_checklist" in handoff_validator_test
    assert "test_validate_plan_closure_handoff_rejects_weak_operator_checklist" in handoff_validator_test
    assert "test_validate_plan_closure_handoff_rejects_missing_operator_commands" in handoff_validator_test
    assert "test_validate_plan_closure_handoff_rejects_weak_operator_commands" in handoff_validator_test
    assert "test_validate_plan_closure_handoff_rejects_operator_commands_without_repo_root" in handoff_validator_test
    assert "test_validate_plan_closure_handoff_rejects_operator_commands_without_python_guard" in handoff_validator_test
    assert "test_validate_plan_closure_handoff_rejects_operator_commands_without_task_selection" in handoff_validator_test
    assert "doge.governance_yaml_shape.v1" in yaml_shape_validator
    assert "REQUIRED_TOP_LEVEL_KEYS" in yaml_shape_validator
    assert "without claiming full YAML parsing" in maturity
    assert "test_validate_governance_yaml_shape_accepts_current_default_files" in yaml_shape_validator_test
    assert "test_validate_governance_yaml_shape_rejects_duplicate_top_level_keys" in yaml_shape_validator_test
    assert "test_validate_governance_yaml_shape_rejects_cr_only_line_endings" in yaml_shape_validator_test
    assert "test_manifest_handoff_input_templates_exist_and_are_json_or_jsonl" in input_template_test
    assert "PLACEHOLDER_PATTERNS" in placeholder_helper
    assert "SENSITIVE_KEYS" in redaction_helper
    assert "*-TEMPLATE" in maturity
    assert "test_placeholder_errors_reject_common_operator_template_tokens" in placeholder_test
    assert "test_secret_leak_errors_reject_credential_shapes_without_printing_values" in redaction_test
    assert "unresolved placeholder" in input_template_test
    assert "test_build_passed_analyst_benchmark_evidence" in analyst_builder_test
    assert "test_build_passed_enterprise_production_evidence" in enterprise_builder_test
    assert "test_build_rejects_missing_enterprise_redaction_flag" in enterprise_builder_test
    assert "test_completed_evidence_requires_explicit_redaction_flags" in enterprise_validator_test
    assert "test_build_approved_provider_approval_evidence" in provider_builder_test
    assert "test_build_rejects_missing_provider_redaction_flag" in provider_builder_test
    assert "test_completed_evidence_requires_explicit_redaction_flags" in provider_validator_test
    assert "test_build_passed_screen_reader_evidence" in screen_reader_builder_test
    assert "test_build_rejects_missing_screen_reader_redaction_flag" in screen_reader_builder_test
    assert "test_completed_evidence_requires_created_at" in screen_reader_validator_test
    assert "test_completed_evidence_requires_explicit_redaction_flags" in screen_reader_validator_test
    assert "test_build_approved_sdk_release_evidence" in sdk_builder_test
    assert "test_build_rejects_missing_sdk_security_flag" in sdk_builder_test
    assert "test_completed_release_requires_explicit_credential_redaction_flag" in sdk_validator_test
    assert manifest["schema"] == "doge.plan_closure_execution_manifest.v1"
    assert manifest["source_plan_check"]["exists"] is True
    assert len(manifest["source_plan_check"]["sha256"]) == 64
    assert manifest["closure_gate"]["summary"]["open"] == 5
    assert manifest["closure_gate"]["summary"]["passed"] == 1
    assert len(manifest["tasks"]) == 6
    manifest_tasks = {item["id"]: item for item in manifest["tasks"]}
    assert manifest_tasks["S017-006"]["can_close_now"] is True
    assert all(
        item["can_close_now"] is False
        for item in manifest["tasks"]
        if item["id"] != "S017-006"
    )
    assert all(item["handoff"]["input_refs"] for item in manifest["tasks"])
    assert any(item["handoff"]["input_templates"] for item in manifest["tasks"])
    assert all(item["handoff"]["build_or_run_command"] for item in manifest["tasks"])
    assert all(item["handoff"]["close_condition"] for item in manifest["tasks"])


def test_analyst_benchmark_template_is_ready_but_not_done():
    maturity = _read("docs/progress/runtime-maturity.yaml")
    audit = _read("docs/progress/kimi-plan-completion-audit.md")
    progress = _read("docs/progress/financial-eval-gold-set.md")
    evidence_report = _read("production/qa/evidence/eval/research-gold-set-2026-06-21.md")
    template = json.loads(_read("production/qa/evidence/eval/analyst-benchmark-template-2026-06-22.json"))

    assert template["schema"] == "doge.analyst_labeled_eval_benchmark.v1"
    assert template["story_id"] == "W3-live"
    assert template["result"] == "not_run"
    assert template["seed_evidence"]["gold_cases"] == "tests/eval/gold_cases.json"
    assert template["materials"]["total_cases"] == 0
    assert template["labels"]["human_citation_labels"] == 0
    assert template["observations"]["raw_sensitive_documents_recorded"] is False
    assert template["redaction_review"]["run_ids_redacted"] is True
    for text in [maturity, audit, progress, evidence_report]:
        assert "analyst-benchmark-template-2026-06-22.json" in text
        assert "validate_analyst_benchmark_evidence.py" in text
    assert "build_analyst_benchmark_evidence.py" in progress
    assert "Failed evidence is allowed only when it" in progress


def test_enterprise_operational_audit_review_records_local_and_production_boundaries():
    text = _read("docs/progress/enterprise-operational-audit-review.md")

    assert "Local operational audit review is complete" in text
    assert "does not make the product production-ready" in text
    assert "SIEM/WORM sink integration" in text
    assert "tenant-scoped audit listing/export/retention" in text
    assert "audit export integrity headers" in text


def test_audit_siem_worm_handoff_packet_keeps_production_sink_pending():
    text = _read("docs/progress/audit-siem-worm-handoff-packet.md")

    assert "Ready for production-operations review, not done" in text
    assert "X-DOGE-Audit-SHA256" in text
    assert "doge.audit_export_manifest.v1" in text
    assert "Production SIEM/WORM remains open" in text
    assert "operator sign-off" in text


def test_production_secret_store_selection_records_process_bridge():
    text = _read("docs/progress/production-secret-store-selection.md")

    assert "ProcessSecretProvider" in text
    assert "DOGE_SECRET_PROVIDER=process" in text
    assert "DOGE_SECRET_PROCESS_COMMAND_JSON" in text
    assert "does not make the product production-ready" in text


def test_s017_soak_evidence_closes_one_hour_gate_without_stable_promotion():
    sprint = _read("production/sprints/sprint-017-external-validation-and-provider-hardening.md")
    maturity = _read("docs/progress/runtime-maturity.yaml")
    summary = _read("production/qa/evidence/soak/daemon-soak-run-20260622T044433/soak-summary.md")
    evidence = json.loads(
        _read("production/qa/evidence/soak/daemon-soak-run-20260622T044433/daemon-soak-20260621T204434Z.json")
    )

    assert "scripts/daemon_soak.py" in sprint
    assert "tests/unit/qa/test_daemon_soak_script.py" in maturity
    assert "S017-005 | done" in sprint
    assert "daemon-soak-run-20260622T044433" in maturity
    assert evidence["summary"] == {"failures": 0, "iterations": 653, "passed": True}
    assert len(evidence["checkpoints"]) == 5
    assert "653" in summary
    assert "| Failures | `0` |" in summary
    assert "production-ready" in summary


def test_sdk_release_approval_packet_keeps_publication_pending():
    text = _read("docs/progress/sdk-release-approval-packet.md")
    evidence = json.loads(_read("production/qa/evidence/sdk/sdk-external-consumer-smoke.json"))
    normalized = " ".join(text.split())

    assert "private: true" in text
    assert "Registry targets" in text
    assert "Version policy" in text
    assert "sdk-release-approval-template-2026-06-22.json" in text
    assert "validate_sdk_release_approval_evidence.py" in text
    assert "build_sdk_release_approval_evidence.py" in text
    assert "compact release-manager decisions" in text
    assert "local external-consumer artifact smoke" in text.lower()
    assert "ready for review, not done" in text
    assert "default validation requires completed release-manager approval evidence" in normalized
    assert evidence["summary"] == {"checks": 2, "failures": 0, "passed": True}
    assert {item["name"] for item in evidence["checks"]} == {
        "python_sdk_external_consumer",
        "typescript_sdk_external_consumer",
    }


def test_sdk_release_approval_template_is_ready_but_not_done():
    sprint = _read("production/sprint-status.yaml")
    sprint_plan = _read("production/sprints/sprint-017-external-validation-and-provider-hardening.md")
    maturity = _read("docs/progress/runtime-maturity.yaml")
    audit = _read("docs/progress/kimi-plan-completion-audit.md")
    template = json.loads(_read("production/qa/evidence/sdk/sdk-release-approval-template-2026-06-22.json"))

    body = re.search(r"- id: S017-007(?P<body>.*?)(?=\n\n  - id: S015)", sprint, re.S).group("body")
    assert "status: review" in body
    assert "validate_sdk_release_approval_evidence.py" in body
    assert "release-manager approval remain pending" in body
    assert template["schema"] == "doge.sdk_release_approval.v1"
    assert template["story_id"] == "S017-007"
    assert template["result"] == "not_run"
    assert {item["language"] for item in template["packages"]} == {"python", "typescript"}
    assert all(item["decision_status"] == "not_decided" for item in template["packages"])
    assert template["security_review"]["contains_credentials"] is False
    for text in [sprint_plan, maturity, audit]:
        assert "sdk-release-approval-template-2026-06-22.json" in text
        assert "validate_sdk_release_approval_evidence.py" in text
        assert "build_sdk_release_approval_evidence.py" in text


def test_browser_sdk_reconnect_evidence_is_supplemented_by_real_agent_reconnect():
    maturity = _read("docs/progress/runtime-maturity.yaml")
    evidence = json.loads(_read("production/qa/evidence/manual/browser-sdk-sse-reconnect-2026-06-22.json"))

    assert evidence["result"] == "passed"
    assert evidence["observed"]["last_event_id_headers"] == ["1", "2"]
    assert evidence["observed"]["event_ids"] == ["2", "3"]
    assert "browser-runtime TypeScript SDK reconnect/replay smoke passed" in maturity
    assert "real doged Research Agent reconnect smoke passed" in maturity


def test_research_agent_doged_reconnect_evidence_keeps_manual_operator_pending():
    maturity = _read("docs/progress/runtime-maturity.yaml")
    sprint = _read("production/sprint-status.yaml")
    evidence = json.loads(_read("production/qa/evidence/manual/research-agent-doged-reconnect-2026-06-22.json"))

    assert evidence["result"] == "passed"
    assert evidence["doged"]["entrypoint"] == "python -m doge.interfaces.daemon.main serve"
    assert evidence["doged"]["model"] == "scripted_no_kimi_key"
    assert evidence["observed"]["status"] == "completed"
    assert evidence["observed"]["forced_disconnects"] == 1
    assert evidence["observed"]["first_released_event_id"] == "1"
    assert evidence["observed"]["last_event_id_headers"][0] is None
    assert evidence["observed"]["last_event_id_headers"][1] == "1"
    assert evidence["observed"]["stream_request_count"] >= 3
    assert "artifact_created" in evidence["observed"]["event_types"]
    assert all(item["passed"] for item in evidence["checks"])
    assert "true manual operator-interruption reconnect session remains open" in maturity
    assert "true manual operator interruption remains deferred" in sprint


def test_research_agent_ax_tree_evidence_supplements_screen_reader_manual_pass():
    maturity = _read("docs/progress/runtime-maturity.yaml")
    sprint = _read("production/sprint-status.yaml")
    evidence = json.loads(_read("production/qa/evidence/manual/research-agent-ax-tree-2026-06-22.json"))

    assert evidence["result"] == "passed"
    assert evidence["summary"]["failed"] == []
    assert evidence["summary"]["checks"]["status_live_region"] is True
    assert evidence["summary"]["checks"]["timeline_list"] is True
    assert "Chrome accessibility-tree smoke" in maturity
    assert "research-agent-screen-reader-manual-2026-06-22.json" in maturity
    assert "id: S017-006" in sprint
    assert "Manual screen-reader pass evidence strictly validates" in sprint


def test_screen_reader_manual_protocol_is_closed_with_completed_evidence():
    maturity = _read("docs/progress/runtime-maturity.yaml")
    sprint = _read("production/sprint-status.yaml")
    protocol = _read("production/qa/screen-reader-manual-protocol-s017.md")
    template = json.loads(
        _read("production/qa/evidence/manual/research-agent-screen-reader-manual-template-2026-06-22.json")
    )

    assert "validate_screen_reader_evidence.py" in protocol
    assert "build_screen_reader_evidence.py" in protocol
    assert "Status: ready for operator execution, not completed" in protocol
    assert template["schema"] == "doge.research_agent_screen_reader_manual.v1"
    assert template["result"] == "not_run"
    assert {item["id"] for item in template["checks"]} == {
        "sr_landmarks_sections",
        "sr_keyboard_primary_controls",
        "sr_status_announcements",
        "sr_approval_context",
        "sr_memo_evidence_quality_timeline",
        "sr_no_keyboard_trap",
    }
    assert "scripts/validate_screen_reader_evidence.py" in maturity
    assert "scripts/build_screen_reader_evidence.py" in maturity
    assert "tests/unit/qa/test_build_screen_reader_evidence.py" in maturity
    assert "build_screen_reader_evidence.py" in sprint
    body = re.search(r"- id: S017-006(?P<body>.*?)(?=\n\n      - id: S017-007)", sprint, re.S).group("body")
    assert "status: done" in body
    assert "research-agent-screen-reader-manual-2026-06-22.json" in sprint


def test_doged_enterprise_static_auth_smoke_keeps_live_idp_pending():
    maturity = _read("docs/progress/runtime-maturity.yaml")
    evidence = json.loads(
        _read("production/qa/evidence/manual/doged-enterprise-static-auth-smoke-2026-06-22.json")
    )

    assert evidence["result"] == "passed"
    assert [item["name"] for item in evidence["checks"]] == [
        "missing_bearer_rejected",
        "wrong_bearer_rejected",
        "authorized_session_create",
        "authorized_document_create_grants_acl",
        "authorized_document_list_sees_created_doc",
        "authorized_document_read",
        "authorized_audit_list_tenant_scoped",
    ]
    assert all(item["passed"] for item in evidence["checks"])
    assert evidence["process"]["shutdown_requested_by_smoke"] is True
    assert evidence["process"]["forced_shutdown"] is False
    assert "doged_static_bearer_smoke" in maturity
    assert "Live IdP/JWKS smoke" in maturity


def test_doged_enterprise_jwks_auth_smoke_keeps_live_idp_pending():
    maturity = _read("docs/progress/runtime-maturity.yaml")
    evidence = json.loads(
        _read("production/qa/evidence/manual/doged-enterprise-jwks-auth-smoke-2026-06-22.json")
    )

    assert evidence["result"] == "passed"
    assert evidence["provider"] == "local_jwks_fixture"
    assert [item["name"] for item in evidence["checks"]] == [
        "missing_bearer_rejected",
        "wrong_audience_rejected",
        "invalid_signature_rejected",
        "authorized_session_create",
        "authorized_document_create_grants_acl",
        "authorized_document_list_sees_created_doc",
        "authorized_audit_list_tenant_scoped",
        "jwks_endpoint_was_used",
    ]
    assert all(item["passed"] for item in evidence["checks"])
    assert evidence["process"]["shutdown_requested_by_smoke"] is True
    assert evidence["process"]["forced_shutdown"] is False
    assert "doged_local_jwks_smoke" in maturity
    assert "Live IdP/JWKS smoke" in maturity


def test_doged_process_secret_smoke_keeps_production_kms_pending():
    maturity = _read("docs/progress/runtime-maturity.yaml")
    evidence = json.loads(
        _read("production/qa/evidence/manual/doged-enterprise-process-secret-auth-smoke-2026-06-22.json")
    )

    assert evidence["result"] == "passed"
    assert evidence["provider"] == "process_secret_fixture"
    assert evidence["secret_provider"] == "process"
    assert evidence["secret_names"] == ["auth.static_bearer_token"]
    assert [item["name"] for item in evidence["checks"]] == [
        "missing_bearer_rejected",
        "wrong_bearer_rejected",
        "authorized_session_create",
        "authorized_document_create_grants_acl",
        "authorized_audit_list_tenant_scoped",
    ]
    assert all(item["passed"] for item in evidence["checks"])
    assert evidence["process"]["shutdown_requested_by_smoke"] is True
    assert evidence["process"]["forced_shutdown"] is False
    assert "doged_process_secret_smoke" in maturity
    assert "Live operator KMS/Vault/cloud command smoke" in maturity


def test_doged_remote_bind_gate_smoke_keeps_live_deployment_pending():
    maturity = _read("docs/progress/runtime-maturity.yaml")
    evidence = json.loads(_read("production/qa/evidence/manual/doged-remote-bind-gate-smoke-2026-06-22.json"))

    assert evidence["result"] == "passed"
    assert evidence["bind_host"] == "0.0.0.0"
    assert [item["name"] for item in evidence["checks"]] == [
        "unapproved_remote_bind_rejected",
        "approved_remote_bind_started_with_enterprise_auth",
    ]
    assert all(item["passed"] for item in evidence["checks"])
    assert evidence["approved_process"]["shutdown_requested_by_smoke"] is True
    assert evidence["approved_process"]["forced_shutdown"] is False
    assert "doged_remote_bind_gate_smoke" in maturity
    assert "Live remote-bind deployment smoke" in maturity


def test_s017_sprint_status_rollup_matches_story_table():
    text = _read("production/sprint-status.yaml")
    s017 = re.search(r"  - id: S017\n(?P<body>.*?)(?=\n  - id: S015\n)", text, re.S)
    assert s017 is not None
    story_blocks = re.findall(
        r"\n      - id: (?P<id>S017-\d{3})(?P<body>.*?)(?=\n      - id: S017-\d{3}|\Z)",
        s017.group("body"),
        re.S,
    )
    stories = []
    for story_id, body in story_blocks:
        stories.append(
            {
                "id": story_id,
                "status": re.search(r"\n        status: ([^\n]+)", body).group(1),
                "priority": re.search(r"\n        priority: ([^\n]+)", body).group(1),
                "epic": re.search(r"\n        epic: ([^\n]+)", body).group(1),
                "blocking_gate": re.search(r"\n        blocking_gate: ([^\n]+)", body).group(1) == "true",
            }
        )

    assert len(stories) == 7

    rollup = re.search(r"rollup:\n(?P<body>.*)\Z", text, re.S)
    assert rollup is not None
    rollup_body = rollup.group("body")

    status_counts = Counter(story["status"] for story in stories)
    priority_counts = Counter(story["priority"] for story in stories)
    epic_counts = Counter(story["epic"] for story in stories)
    open_blocking = [
        story["id"]
        for story in stories
        if story["blocking_gate"] and story["status"] not in {"done", "deferred"}
    ]

    assert "  sprint: S017" in rollup_body
    assert f"  total_stories: {len(stories)}" in rollup_body
    for status in ["todo", "in_progress", "blocked", "review", "done", "deferred"]:
        assert f"    {status}: {status_counts[status]}" in rollup_body
    for priority in ["HIGH", "MED", "LOW"]:
        assert f"    {priority}: {priority_counts[priority]}" in rollup_body
    for epic, count in epic_counts.items():
        assert f"    {epic}: {count}" in rollup_body
    for story_id in open_blocking:
        assert f"    - {story_id}" in rollup_body
