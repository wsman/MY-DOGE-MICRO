from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_plan_closure_manifest import DEFAULT_OUTPUT
from scripts.analyst_trend_history import validate_trend_history_jsonl
from scripts.evidence_placeholders import placeholder_errors
from scripts.evidence_redaction import secret_leak_errors
from scripts.validate_plan_closure_gate import validate_all
from scripts.validate_plan_closure_handoff import validate_workspace
from scripts.validate_plan_closure_manifest import validate as validate_manifest


SCRIPT_RE = re.compile(r"scripts[\\/][A-Za-z0-9_.\\/-]+?\.py")
GOLD_CASES_PATH = ROOT / "tests" / "eval" / "gold_cases.json"
PROVIDER_CAPABILITIES = {
    "announcements",
    "consensus",
    "financial_statements",
    "industry_classification",
    "risk_factors",
}
PROVIDER_APPROVAL_FIELDS = [
    "approved_provider",
    "license_scope",
    "fixture_storage_policy",
    "freshness_requirement",
    "provenance_requirement",
]
SDK_LANGUAGES = {"python", "typescript"}
SDK_APPROVAL_FIELDS = [
    "approved_package_name",
    "registry_target",
    "package_name_ownership",
    "version_policy",
    "changelog_policy",
    "registry_consumer_smoke",
]
SDK_SECURITY_APPROVAL_FIELDS = [
    "no_credentials_in_package_config",
    "typescript_sources_excluded_from_tarball",
    "redaction_behavior_documented",
]
ENTERPRISE_PRODUCTION_CHECK_IDS = {
    "live_idp_jwks",
    "live_remote_bind_deployment",
    "production_data_isolation_review",
    "production_secret_store_command",
    "siem_worm_export",
}
SCREEN_READER_CHECK_IDS = {
    "sr_approval_context",
    "sr_keyboard_primary_controls",
    "sr_landmarks_sections",
    "sr_memo_evidence_quality_timeline",
    "sr_no_keyboard_trap",
    "sr_status_announcements",
}
SCREEN_READER_ENVIRONMENT_FIELDS = [
    "platform",
    "browser",
    "browser_version",
    "screen_reader",
    "screen_reader_version",
    "web_url",
]
DECISION_STATUSES = {"approved", "needs_revision", "not_decided", "rejected"}
OBSERVATION_STATUSES = {"blocked", "failed", "not_run", "passed"}
UNFILLED_MARKERS = {"pending", "not_decided", "not run", "not_run", "template", "tbd", "todo"}


def build_preflight(
    *,
    manifest_path: Path = DEFAULT_OUTPUT,
    handoff_workspace: Path | None = None,
    require_external_inputs: bool = False,
    task_ids: set[str] | None = None,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_errors = validate_manifest(manifest)
    gate = validate_all(allow_open=True)
    handoff_payload = _load_handoff_payload(handoff_workspace) if handoff_workspace else None
    handoff_tasks = _handoff_tasks_by_id(handoff_payload)
    requested_task_ids = set(task_ids or set())
    manifest_tasks = manifest.get("tasks", [])
    all_task_ids = {
        task["id"]
        for task in manifest_tasks
        if isinstance(task, dict) and isinstance(task.get("id"), str)
    }
    unknown_task_ids = sorted(requested_task_ids - all_task_ids)
    selected_tasks = [
        task
        for task in manifest_tasks
        if not requested_task_ids or task.get("id") in requested_task_ids
    ]
    tasks = [
        _preflight_task(
            task,
            handoff_task=handoff_tasks.get(task.get("id")),
            force_external_checks=task.get("id") in requested_task_ids,
        )
        for task in selected_tasks
    ]
    handoff_errors = validate_workspace(handoff_workspace, manifest_path=manifest_path) if handoff_workspace else []
    optional_checks = _optional_checks(
        include_live_kimi=any(
            task["id"] == "S017-002" and task["external_inputs_required"]
            for task in tasks
        )
    )

    infrastructure_errors = []
    infrastructure_errors.extend(f"manifest: {error}" for error in manifest_errors)
    infrastructure_errors.extend(f"unknown task id: {task_id}" for task_id in unknown_task_ids)
    if not gate.get("acceptable"):
        infrastructure_errors.append("closure gate is not acceptable under --allow-open")
    for task in tasks:
        infrastructure_errors.extend(f"{task['id']}: {error}" for error in task["infrastructure_errors"])
    infrastructure_errors.extend(f"handoff: {error}" for error in handoff_errors)

    external_blockers = [
        blocker
        for task in tasks
        for blocker in task["external_blockers"]
    ]
    external_blockers.extend(optional_checks["blocking_errors"])

    infrastructure_ready = not infrastructure_errors
    external_inputs_ready = not external_blockers
    result = "ready" if infrastructure_ready and external_inputs_ready else "pending_external_inputs"
    if not infrastructure_ready:
        result = "failed"
    if require_external_inputs and infrastructure_ready and not external_inputs_ready:
        result = "failed"

    return {
        "schema": "doge.plan_closure_external_preflight.v1",
        "manifest": _display_path(manifest_path),
        "handoff_workspace": _display_path(handoff_workspace) if handoff_workspace else None,
        "requested_task_ids": sorted(requested_task_ids),
        "result": result,
        "infrastructure_ready": infrastructure_ready,
        "external_inputs_ready": external_inputs_ready,
        "require_external_inputs": require_external_inputs,
        "secret_values_redacted": True,
        "closure_gate": {
            "result": gate.get("result"),
            "acceptable_with_open_items": gate.get("acceptable"),
            "summary": gate.get("summary"),
            "production_ready_false": gate.get("posture", {}).get("production_ready_false"),
            "stable_declaration_forbidden": gate.get("posture", {}).get("stable_declaration_forbidden"),
        },
        "infrastructure_errors": infrastructure_errors,
        "external_blockers": external_blockers,
        "optional_checks": optional_checks,
        "tasks": tasks,
    }


def _preflight_task(
    task: dict[str, Any],
    *,
    handoff_task: dict[str, Any] | None = None,
    force_external_checks: bool = False,
) -> dict[str, Any]:
    handoff = task.get("handoff", {})
    infrastructure_errors: list[str] = []
    external_blockers: list[str] = []
    command_checks = [
        _command_check("validator", task.get("validator_command")),
        _command_check("builder_or_runner", handoff.get("build_or_run_command")),
    ]
    for check in command_checks:
        if not check["exists"]:
            infrastructure_errors.append(f"{check['kind']} script missing: {check['script']}")

    current_evidence = _path_check(task.get("current_evidence"))
    if not current_evidence["exists"]:
        infrastructure_errors.append(f"current evidence missing: {task.get('current_evidence')}")

    output_dir = _output_dir_check(handoff.get("output_ref"))
    if not output_dir["exists"]:
        infrastructure_errors.append(f"output directory missing: {output_dir['path']}")

    template_checks = [_path_check(template) for template in handoff.get("input_templates", [])]
    for check in template_checks:
        if not check["exists"]:
            infrastructure_errors.append(f"input template missing: {check['path']}")

    draft_bindings = _draft_bindings_by_ref(handoff_task)
    input_ref_checks = [
        _input_ref_check(
            input_ref,
            draft_binding=draft_bindings.get(input_ref),
            required_results=task.get("required_results", []),
        )
        for input_ref in handoff.get("input_refs", [])
    ]
    external_inputs_required = force_external_checks or not _task_is_already_passed(task)
    if external_inputs_required:
        for check in input_ref_checks:
            if check["kind"] == "required_env" and not check["ready"]:
                external_blockers.append(f"{task['id']}: required env not ready: {check['name']}")
            if check["kind"] == "required_file" and not check["ready"]:
                external_blockers.append(f"{task['id']}: required file not ready: {check['path']}")
            if check["kind"] == "dated_file_placeholder":
                external_blockers.append(f"{task['id']}: dated input ref must be filled: {check['path']}")
            if check["kind"] == "workspace_draft_input" and not check["ready"]:
                if not check["exists"]:
                    reason = "missing"
                elif not check["differs_from_template"]:
                    reason = "still matches source template"
                else:
                    reason = "invalid content: " + "; ".join(check["content_errors"])
                external_blockers.append(f"{task['id']}: workspace draft input not ready ({reason}): {check['path']}")

    return {
        "id": task["id"],
        "title": task["title"],
        "required_results": task["required_results"],
        "current_status": task["current_status"],
        "current_result": task["current_result"],
        "external_inputs_required": external_inputs_required,
        "command_checks": command_checks,
        "current_evidence": current_evidence,
        "output_dir": output_dir,
        "input_templates": template_checks,
        "input_refs": input_ref_checks,
        "infrastructure_errors": infrastructure_errors,
        "external_blockers": external_blockers,
        "next_action": task["next_action"],
    }


def _task_is_already_passed(task: dict[str, Any]) -> bool:
    return task.get("current_status") == "passed" and task.get("can_close_now") is True


def _command_check(kind: str, command: str | None) -> dict[str, Any]:
    script = _extract_script(command or "")
    path = _repo_path(script) if script else None
    return {
        "kind": kind,
        "command": command,
        "script": script,
        "exists": bool(path and path.exists()),
    }


def _extract_script(command: str) -> str | None:
    match = SCRIPT_RE.search(command)
    if not match:
        return None
    return match.group(0).replace("\\", "/")


def _path_check(value: str | None) -> dict[str, Any]:
    path = _repo_path(value) if value else None
    return {
        "path": value,
        "exists": bool(path and path.exists()),
    }


def _output_dir_check(value: str | None) -> dict[str, Any]:
    if not value:
        return {"path": None, "exists": False}
    normalized = value.replace("YYYY-MM-DD", "2030-01-02").replace("\\", "/")
    parent = (ROOT / Path(normalized)).parent
    return {
        "path": _display_path(parent),
        "exists": parent.exists(),
    }


def _input_ref_check(
    value: str,
    *,
    draft_binding: dict[str, str] | None = None,
    required_results: list[str],
) -> dict[str, Any]:
    if value.startswith("optional:env:"):
        name, expected = _parse_env_ref(value.removeprefix("optional:env:"))
        present, matches = _env_state(name, expected)
        return {
            "kind": "optional_env",
            "ref": value,
            "name": name,
            "expected": expected,
            "present": present,
            "matches_expected": matches,
            "ready": (not present) or matches,
        }
    if value.startswith("env:"):
        name, expected = _parse_env_ref(value.removeprefix("env:"))
        present, matches = _env_state(name, expected)
        return {
            "kind": "required_env",
            "ref": value,
            "name": name,
            "expected": expected,
            "present": present,
            "matches_expected": matches,
            "ready": present and matches,
        }
    if draft_binding is not None:
        return _workspace_draft_input_check(value, draft_binding, required_results=required_results)
    if "YYYY-MM-DD" in value:
        return {
            "kind": "dated_file_placeholder",
            "ref": value,
            "path": value,
            "ready": False,
        }
    check = _path_check(value)
    return {
        "kind": "required_file",
        "ref": value,
        "path": value,
        "exists": check["exists"],
        "ready": check["exists"],
    }


def _workspace_draft_input_check(
    input_ref: str,
    binding: dict[str, str],
    *,
    required_results: list[str],
) -> dict[str, Any]:
    draft_path = _repo_path(binding.get("prepared_input"))
    source_path = _repo_path(binding.get("source_template"))
    exists = draft_path.exists()
    source_exists = source_path.exists()
    differs_from_template = exists and source_exists and draft_path.read_bytes() != source_path.read_bytes()
    content_errors = _draft_content_errors(draft_path, source_path, required_results=required_results) if exists else []
    return {
        "kind": "workspace_draft_input",
        "ref": input_ref,
        "path": binding.get("prepared_input"),
        "source_template": binding.get("source_template"),
        "exists": exists,
        "source_template_exists": source_exists,
        "differs_from_template": differs_from_template,
        "content_valid": not content_errors,
        "content_errors": content_errors,
        "ready": exists and source_exists and differs_from_template and not content_errors,
    }


def _draft_content_errors(draft_path: Path, source_path: Path, *, required_results: list[str]) -> list[str]:
    name = source_path.name
    if draft_path.suffix == ".jsonl":
        if name.startswith("trend-history-"):
            expected_case_count = _gold_case_summary().get("case_count")
            return validate_trend_history_jsonl(
                draft_path,
                expected_case_count=expected_case_count if isinstance(expected_case_count, int) else None,
                subject="draft input",
            )
        return _jsonl_content_errors(draft_path)
    if draft_path.suffix != ".json":
        return []
    try:
        payload = json.loads(draft_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc.msg}"]
    if not isinstance(payload, dict):
        return ["JSON draft must be an object"]

    if name.startswith("provider-decisions-"):
        errors = _approval_decision_errors(
            payload,
            required_results=required_results,
            result_values={"approved", "needs_revision", "rejected"},
            actor_key="operator",
            collection_key="decisions",
        )
        errors.extend(placeholder_errors(payload, subject="draft input"))
        errors.extend(secret_leak_errors(payload, subject="draft input"))
        return errors
    if name.startswith("sdk-release-decisions-"):
        errors = _approval_decision_errors(
            payload,
            required_results=required_results,
            result_values={"approved", "needs_revision", "rejected"},
            actor_key="release_manager",
            collection_key="packages",
        )
        errors.extend(placeholder_errors(payload, subject="draft input"))
        errors.extend(secret_leak_errors(payload, subject="draft input"))
        return errors
    if name.startswith("enterprise-production-observations-"):
        errors = _observation_errors(payload, required_results=required_results, require_environment=False)
        errors.extend(_enterprise_production_observation_errors(payload))
        errors.extend(placeholder_errors(payload, subject="draft input"))
        errors.extend(secret_leak_errors(payload, subject="draft input"))
        return errors
    if name.startswith("screen-reader-observations-"):
        errors = _observation_errors(payload, required_results=required_results, require_environment=True)
        errors.extend(_screen_reader_observation_errors(payload))
        errors.extend(placeholder_errors(payload, subject="draft input"))
        errors.extend(secret_leak_errors(payload, subject="draft input"))
        return errors
    if name.startswith("live-kimi-observations-"):
        observations = payload.get("observations", payload)
        errors = [] if isinstance(observations, dict) and observations else ["observations must be a non-empty object"]
        if isinstance(observations, dict):
            errors.extend(_live_observation_case_errors(observations))
        errors.extend(placeholder_errors(payload, subject="draft input"))
        errors.extend(secret_leak_errors(payload, subject="draft input"))
        return errors
    if name.startswith("approved-thresholds-"):
        errors = _threshold_errors(payload)
        errors.extend(placeholder_errors(payload, subject="draft input"))
        errors.extend(secret_leak_errors(payload, subject="draft input"))
        return errors
    if name.startswith("material-manifest-"):
        errors = _count_manifest_errors(payload, "case_count")
        expected_case_count = _gold_case_summary().get("case_count")
        if isinstance(expected_case_count, int) and payload.get("case_count") != expected_case_count:
            errors.append(f"case_count must match gold case count: {expected_case_count}")
        errors.extend(placeholder_errors(payload, subject="draft input"))
        errors.extend(secret_leak_errors(payload, subject="draft input"))
        return errors
    if name.startswith("label-manifest-"):
        errors = []
        expected = _gold_case_summary()
        for key in ["human_citation_labels", "human_numerical_labels", "insufficient_evidence_labels"]:
            value = payload.get(key)
            if not isinstance(value, int) or value <= 0:
                errors.append(f"{key} must be a positive integer")
                continue
            minimum = expected.get(key)
            if isinstance(minimum, int) and value < minimum:
                errors.append(f"{key} must be at least gold label count: {minimum}")
        if payload.get("status") == "template":
            errors.append("status must not be template")
        errors.extend(placeholder_errors(payload, subject="draft input"))
        errors.extend(secret_leak_errors(payload, subject="draft input"))
        return errors
    errors = placeholder_errors(payload, subject="draft input")
    errors.extend(secret_leak_errors(payload, subject="draft input"))
    return errors


def _approval_decision_errors(
    payload: dict[str, Any],
    *,
    required_results: list[str],
    result_values: set[str],
    actor_key: str,
    collection_key: str,
) -> list[str]:
    errors: list[str] = []
    result = payload.get("result")
    if result not in result_values:
        errors.append(f"result must be one of {', '.join(sorted(result_values))}")
    elif required_results and result not in required_results:
        errors.append(f"result must be one of required_results: {', '.join(required_results)}")
    actor = payload.get(actor_key)
    if not isinstance(actor, dict) or not _non_empty_string(actor.get("role")) or not _non_empty_string(actor.get("initials")):
        errors.append(f"{actor_key}.role and {actor_key}.initials are required")
    if not _non_empty_string(payload.get("approved_at")):
        errors.append("approved_at is required")
    collection = payload.get(collection_key)
    if not ((isinstance(collection, dict) and collection) or (isinstance(collection, list) and collection)):
        errors.append(f"{collection_key} must be a non-empty object or list")
    elif collection_key == "decisions":
        errors.extend(_provider_decision_errors(payload, result=result))
    elif collection_key == "packages":
        errors.extend(_sdk_release_decision_errors(payload, result=result))
    return errors


def _provider_decision_errors(payload: dict[str, Any], *, result: Any) -> list[str]:
    errors: list[str] = []
    decisions, map_errors = _keyed_items(
        payload.get("decisions"),
        item_key="capability",
        expected_keys=PROVIDER_CAPABILITIES,
        collection_key="decisions",
    )
    errors.extend(map_errors)
    for capability, item in sorted(decisions.items()):
        status = item.get("decision_status")
        if status not in DECISION_STATUSES:
            errors.append(f"{capability}: decision_status must be one of {', '.join(sorted(DECISION_STATUSES))}")
        if result == "approved" and status != "approved":
            errors.append(f"{capability}: approved draft requires decision_status=approved")
        for key in ["preferred_provider_direction", "local_fallback", "notes"]:
            _require_filled_value(item.get(key), f"{capability}.{key}", errors)
        if result == "approved":
            for key in PROVIDER_APPROVAL_FIELDS:
                _require_filled_value(item.get(key), f"{capability}.{key}", errors)

    redaction = payload.get("redaction_review")
    if not isinstance(redaction, dict):
        errors.append("redaction_review must be an object")
        return errors
    _require_false(redaction.get("contains_credentials"), "redaction_review.contains_credentials", errors)
    _require_false(redaction.get("contains_proprietary_data"), "redaction_review.contains_proprietary_data", errors)
    if result == "approved" and redaction.get("repository_storage_approved") is not True:
        errors.append("approved draft requires redaction_review.repository_storage_approved=true")
    return errors


def _sdk_release_decision_errors(payload: dict[str, Any], *, result: Any) -> list[str]:
    errors: list[str] = []
    packages, map_errors = _keyed_items(
        payload.get("packages"),
        item_key="language",
        expected_keys=SDK_LANGUAGES,
        collection_key="packages",
    )
    errors.extend(map_errors)
    for language, item in sorted(packages.items()):
        status = item.get("decision_status")
        if status not in DECISION_STATUSES:
            errors.append(f"{language}: decision_status must be one of {', '.join(sorted(DECISION_STATUSES))}")
        if result == "approved" and status != "approved":
            errors.append(f"{language}: approved draft requires decision_status=approved")
        if result == "approved":
            for key in SDK_APPROVAL_FIELDS:
                _require_filled_value(item.get(key), f"{language}.{key}", errors)
            _require_filled_value(item.get("notes"), f"{language}.notes", errors)

    security = payload.get("security_review")
    if not isinstance(security, dict):
        errors.append("security_review must be an object")
        return errors
    _require_false(security.get("contains_credentials"), "security_review.contains_credentials", errors)
    if result == "approved":
        for key in SDK_SECURITY_APPROVAL_FIELDS:
            if security.get(key) is not True:
                errors.append(f"approved draft requires security_review.{key}=true")
    return errors


def _keyed_items(
    value: Any,
    *,
    item_key: str,
    expected_keys: set[str],
    collection_key: str,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    errors: list[str] = []
    items: dict[str, dict[str, Any]] = {}
    if isinstance(value, dict):
        for key, raw_item in value.items():
            if not isinstance(raw_item, dict):
                errors.append(f"{collection_key}.{key} must be an object")
                continue
            item = dict(raw_item)
            item[item_key] = key
            items[key] = item
    elif isinstance(value, list):
        for raw_item in value:
            if not isinstance(raw_item, dict):
                errors.append(f"each {collection_key} item must be an object")
                continue
            key = raw_item.get(item_key)
            if not isinstance(key, str) or not key.strip():
                errors.append(f"each {collection_key} item requires {item_key}")
                continue
            if key in items:
                errors.append(f"duplicate {collection_key} item: {key}")
            items[key] = raw_item
    else:
        return {}, errors

    missing = expected_keys - set(items)
    extra = set(items) - expected_keys
    if missing:
        errors.append(f"missing {collection_key}: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"unexpected {collection_key}: {', '.join(sorted(extra))}")
    return items, errors


def _require_filled_value(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} must be filled")
        return
    normalized = value.strip().lower()
    if (
        normalized in UNFILLED_MARKERS
        or normalized.startswith("replace this template")
        or normalized.startswith("operator-secure-store://replace")
    ):
        errors.append(f"{field} must be filled and not pending/template text")


def _require_false(value: Any, field: str, errors: list[str]) -> None:
    if value is not False:
        errors.append(f"{field} must be false")


def _observation_errors(payload: dict[str, Any], *, required_results: list[str], require_environment: bool) -> list[str]:
    errors: list[str] = []
    result = payload.get("result")
    if result not in {"passed", "failed"}:
        errors.append("result must be passed or failed")
    elif required_results and result not in required_results:
        errors.append(f"result must be one of required_results: {', '.join(required_results)}")
    if not _non_empty_string(payload.get("executed_at")):
        errors.append("executed_at is required")
    actor = payload.get("operator")
    if not isinstance(actor, dict) or not _non_empty_string(actor.get("role")) or not _non_empty_string(actor.get("initials")):
        errors.append("operator.role and operator.initials are required")
    if require_environment and not isinstance(payload.get("environment"), dict):
        errors.append("environment is required")
    checks = payload.get("checks")
    if not ((isinstance(checks, dict) and checks) or (isinstance(checks, list) and checks)):
        errors.append("checks must be a non-empty object")
    if require_environment and not _non_empty_string(payload.get("summary")):
        errors.append("summary is required")
    return errors


def _enterprise_production_observation_errors(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    result = payload.get("result")
    checks, map_errors = _keyed_items(
        payload.get("checks"),
        item_key="id",
        expected_keys=ENTERPRISE_PRODUCTION_CHECK_IDS,
        collection_key="checks",
    )
    errors.extend(map_errors)
    for check_id, item in sorted(checks.items()):
        status = item.get("status")
        if status not in OBSERVATION_STATUSES:
            errors.append(f"{check_id}: status must be one of {', '.join(sorted(OBSERVATION_STATUSES))}")
        if result == "passed" and status != "passed":
            errors.append(f"{check_id}: passed draft requires status=passed")
        if result in {"passed", "failed"} and status in {"passed", "failed", "blocked"}:
            _require_filled_value(item.get("evidence_ref"), f"{check_id}.evidence_ref", errors)
        if result == "failed" and status in {"failed", "blocked"} and not _non_empty_string(item.get("issue_ref")):
            errors.append(f"{check_id}: failed/blocked draft requires issue_ref")

    if result == "failed" and not payload.get("issue_refs"):
        errors.append("failed draft requires issue_refs")

    redaction = payload.get("redaction_review")
    if not isinstance(redaction, dict):
        errors.append("redaction_review must be an object")
        return errors
    for key in ["contains_credentials", "contains_raw_subjects", "contains_proprietary_customer_data"]:
        _require_false(redaction.get(key), f"redaction_review.{key}", errors)
    return errors


def _screen_reader_observation_errors(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    result = payload.get("result")
    environment = payload.get("environment")
    if isinstance(environment, dict):
        for key in SCREEN_READER_ENVIRONMENT_FIELDS:
            _require_filled_value(environment.get(key), f"environment.{key}", errors)

    checks, map_errors = _keyed_items(
        payload.get("checks"),
        item_key="id",
        expected_keys=SCREEN_READER_CHECK_IDS,
        collection_key="checks",
    )
    errors.extend(map_errors)
    for check_id, item in sorted(checks.items()):
        status = item.get("status")
        if status not in OBSERVATION_STATUSES:
            errors.append(f"{check_id}: status must be one of {', '.join(sorted(OBSERVATION_STATUSES))}")
        if result == "passed" and status != "passed":
            errors.append(f"{check_id}: passed draft requires status=passed")
        if result == "failed" and status in {"failed", "blocked"} and not _non_empty_string(item.get("issue_ref")):
            errors.append(f"{check_id}: failed/blocked draft requires issue_ref")
        if result in {"passed", "failed"}:
            _require_filled_value(item.get("notes"), f"{check_id}.notes", errors)

    issues = payload.get("issues")
    if result == "failed" and not issues:
        errors.append("failed draft requires at least one issue reference")
    if issues is not None and not isinstance(issues, list):
        errors.append("issues must be a list when present")

    redaction = payload.get("redaction_review")
    if not isinstance(redaction, dict):
        errors.append("redaction_review must be an object")
        return errors
    _require_false(redaction.get("contains_secrets"), "redaction_review.contains_secrets", errors)
    _require_false(
        redaction.get("contains_sensitive_documents"),
        "redaction_review.contains_sensitive_documents",
        errors,
    )
    return errors


def _threshold_errors(payload: dict[str, Any]) -> list[str]:
    required = {
        "citation_precision_min",
        "cost_usd_p95_max",
        "latency_p95_ms_max",
        "numerical_consistency_min",
        "retrieval_precision_min",
        "retrieval_recall_min",
        "usage_cost_record_coverage_min",
    }
    errors: list[str] = []
    for key in sorted(required):
        if not isinstance(payload.get(key), (int, float)):
            errors.append(f"{key} must be numeric")
    for key in sorted(required):
        value = payload.get(key)
        if key.endswith("_min") and isinstance(value, (int, float)) and not 0 <= value <= 1:
            errors.append(f"{key} must be between 0 and 1")
        if key.endswith("_max") and isinstance(value, (int, float)) and value <= 0:
            errors.append(f"{key} must be positive")
    return errors


def _live_observation_case_errors(observations: dict[str, Any]) -> list[str]:
    summary = _gold_case_summary()
    expected_ids = summary.get("case_ids")
    if not isinstance(expected_ids, set):
        return ["gold case ids are unavailable"]
    case_requirements = summary.get("case_requirements")
    if not isinstance(case_requirements, dict):
        return ["gold case requirements are unavailable"]
    observed_ids = set(observations)
    missing = sorted(expected_ids - observed_ids)
    unexpected = sorted(observed_ids - expected_ids)
    errors: list[str] = []
    if missing:
        errors.append(f"observations missing gold case ids: {', '.join(missing[:5])}" + ("..." if len(missing) > 5 else ""))
    if unexpected:
        errors.append(f"observations include unknown case ids: {', '.join(unexpected[:5])}" + ("..." if len(unexpected) > 5 else ""))
    for case_id, value in observations.items():
        if case_id not in expected_ids:
            continue
        if not isinstance(value, dict):
            errors.append(f"observations.{case_id} must be an object")
            continue
        requirements = case_requirements.get(case_id, {})
        expected_evidence_ids = requirements.get("expected_evidence_ids", set())
        expected_number_metrics = requirements.get("expected_number_metrics", set())
        errors.extend(_live_observation_detail_errors(case_id, value, expected_evidence_ids, expected_number_metrics))
    return errors


def _live_observation_detail_errors(
    case_id: str,
    observation: dict[str, Any],
    expected_evidence_ids: set[str],
    expected_number_metrics: set[str],
) -> list[str]:
    errors: list[str] = []
    retrieved = observation.get("retrieved_evidence_ids")
    cited = observation.get("cited_evidence_ids")
    numbers = observation.get("numbers")
    usage = observation.get("usage")
    if not _string_list_value(retrieved):
        errors.append(f"observations.{case_id}.retrieved_evidence_ids must be a list of strings")
    if expected_evidence_ids and not retrieved:
        errors.append(f"observations.{case_id}.retrieved_evidence_ids must include retrieval output")
    if not _string_list_value(cited):
        errors.append(f"observations.{case_id}.cited_evidence_ids must be a list of strings")
    if expected_evidence_ids and not cited:
        errors.append(f"observations.{case_id}.cited_evidence_ids must include citation output")
    if not isinstance(numbers, dict):
        errors.append(f"observations.{case_id}.numbers must be an object")
    else:
        for metric in sorted(expected_number_metrics):
            value = numbers.get(metric)
            if not isinstance(value, (int, float)):
                errors.append(f"observations.{case_id}.numbers.{metric} must be numeric")
    if not isinstance(usage, dict):
        errors.append(f"observations.{case_id}.usage must be an object")
    else:
        cost = usage.get("cost_usd")
        latency = usage.get("latency_ms")
        if not isinstance(cost, (int, float)) or cost < 0:
            errors.append(f"observations.{case_id}.usage.cost_usd must be a non-negative number")
        if not isinstance(latency, (int, float)) or latency <= 0:
            errors.append(f"observations.{case_id}.usage.latency_ms must be a positive number")
    for raw_key in ["run_id", "raw_run_id", "session_id", "raw_session_id"]:
        if raw_key in observation:
            errors.append(f"observations.{case_id}.{raw_key} must not be recorded")
    return errors


def _string_list_value(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def _gold_case_summary() -> dict[str, Any]:
    if not GOLD_CASES_PATH.exists():
        return {}
    try:
        cases = json.loads(GOLD_CASES_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(cases, list):
        return {}
    case_ids = {
        str(case.get("id"))
        for case in cases
        if isinstance(case, dict) and isinstance(case.get("id"), str)
    }
    case_requirements = {
        str(case["id"]): {
            "expected_evidence_ids": {
                str(citation["evidence_id"])
                for citation in case.get("expected_citations", [])
                if isinstance(citation, dict) and isinstance(citation.get("evidence_id"), str)
            },
            "expected_number_metrics": {
                str(number["metric"])
                for number in case.get("expected_numbers", [])
                if isinstance(number, dict) and isinstance(number.get("metric"), str)
            },
        }
        for case in cases
        if isinstance(case, dict) and isinstance(case.get("id"), str)
    }
    return {
        "case_count": len(case_ids),
        "case_ids": case_ids,
        "case_requirements": case_requirements,
        "human_citation_labels": sum(
            len(case.get("expected_citations", []))
            for case in cases
            if isinstance(case, dict) and isinstance(case.get("expected_citations"), list)
        ),
        "human_numerical_labels": sum(
            len(case.get("expected_numbers", []))
            for case in cases
            if isinstance(case, dict) and isinstance(case.get("expected_numbers"), list)
        ),
        "insufficient_evidence_labels": sum(
            1
            for case in cases
            if isinstance(case, dict)
            for claim in case.get("expected_claims", [])
            if isinstance(claim, dict) and claim.get("expected_status") == "insufficient_evidence"
        ),
    }


def _count_manifest_errors(payload: dict[str, Any], count_key: str) -> list[str]:
    errors: list[str] = []
    if payload.get("status") == "template":
        errors.append("status must not be template")
    if not isinstance(payload.get(count_key), int) or payload[count_key] <= 0:
        errors.append(f"{count_key} must be a positive integer")
    return errors


def _jsonl_content_errors(path: Path) -> list[str]:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return ["JSONL draft must contain at least one row"]
    errors: list[str] = []
    template_rows = 0
    for index, line in enumerate(lines, 1):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {index}: invalid JSON: {exc.msg}")
            continue
        if isinstance(payload, dict) and payload.get("status") == "template":
            template_rows += 1
        if isinstance(payload, dict):
            errors.extend(
                f"line {index}: {error}"
                for error in placeholder_errors(payload, subject="draft input")
            )
            errors.extend(
                f"line {index}: {error}"
                for error in secret_leak_errors(payload, subject="draft input")
            )
    if template_rows == len(lines):
        errors.append("JSONL draft must not contain only template rows")
    return errors


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _load_handoff_payload(workspace: Path | None) -> dict[str, Any] | None:
    if workspace is None:
        return None
    handoff_path = workspace if workspace.name == "handoff.json" else workspace / "handoff.json"
    if not handoff_path.exists():
        return None
    return json.loads(handoff_path.read_text(encoding="utf-8"))


def _handoff_tasks_by_id(payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not payload or not isinstance(payload.get("tasks"), list):
        return {}
    return {
        task["id"]: task
        for task in payload["tasks"]
        if isinstance(task, dict) and isinstance(task.get("id"), str)
    }


def _draft_bindings_by_ref(handoff_task: dict[str, Any] | None) -> dict[str, dict[str, str]]:
    if not handoff_task:
        return {}
    plan = handoff_task.get("workspace_command_plan")
    if not isinstance(plan, dict):
        return {}
    bindings = plan.get("prepared_input_bindings")
    if not isinstance(bindings, list):
        return {}
    return {
        binding["input_ref"]: binding
        for binding in bindings
        if isinstance(binding, dict) and isinstance(binding.get("input_ref"), str)
    }


def _parse_env_ref(value: str) -> tuple[str, str | None]:
    if "=" not in value:
        return value, None
    name, expected = value.split("=", 1)
    return name, expected


def _env_state(name: str, expected: str | None) -> tuple[bool, bool]:
    value = os.environ.get(name)
    present = value is not None and value != ""
    if not present:
        return False, False
    if expected is None:
        return True, True
    return True, value == expected


def _optional_checks(*, include_live_kimi: bool) -> dict[str, Any]:
    agent_sdk_requested = include_live_kimi and os.environ.get("DOGE_LIVE_KIMI_AGENT_SDK") == "1"
    agent_sdk_available = importlib.util.find_spec("kimi_agent_sdk") is not None if include_live_kimi else False
    blocking_errors: list[str] = []
    if agent_sdk_requested and not agent_sdk_available:
        blocking_errors.append("DOGE_LIVE_KIMI_AGENT_SDK=1 but kimi_agent_sdk is not importable")
    return {
        "kimi_agent_sdk_requested": agent_sdk_requested,
        "kimi_agent_sdk_available": agent_sdk_available,
        "blocking_errors": blocking_errors,
    }


def _repo_path(value: str | None) -> Path:
    if not value:
        return ROOT
    normalized = Path(str(value).replace("\\", "/"))
    if normalized.is_absolute():
        return normalized
    return ROOT / normalized


def _display_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preflight the 9b77f9c external closure execution window.")
    parser.add_argument("--manifest", default=str(DEFAULT_OUTPUT), help="Execution manifest JSON path.")
    parser.add_argument("--handoff-workspace", help="Optional prepared handoff workspace to validate.")
    parser.add_argument(
        "--require-external-inputs",
        action="store_true",
        help="Return nonzero when required env vars or external input files are still missing.",
    )
    parser.add_argument(
        "--task-id",
        action="append",
        default=[],
        help="Limit preflight to one external closure task. Repeat to check multiple tasks.",
    )
    args = parser.parse_args(argv)

    payload = build_preflight(
        manifest_path=Path(args.manifest),
        handoff_workspace=Path(args.handoff_workspace) if args.handoff_workspace else None,
        require_external_inputs=args.require_external_inputs,
        task_ids=set(args.task_id),
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["result"] != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
