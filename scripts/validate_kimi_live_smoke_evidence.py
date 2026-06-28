from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evidence_placeholders import placeholder_errors
from scripts.evidence_redaction import secret_leak_errors


SCHEMA = "doge.kimi_live_smoke.v1"
STORY_ID = "S017-002"
BASE_REQUIRED_SCENARIOS = {"text_k26", "vision_base64"}
FULL_CLOSURE_SCENARIOS = {"text_k26", "files_upload", "vision_base64", "agent_sdk_optional"}
OPTIONAL_SCENARIOS = {"files_upload", "agent_sdk_optional"}
ALLOWED_SECRET_KEYS = {
    "api_key_recorded",
    "MOONSHOT_API_KEY_PRESENT",
    "raw_file_id_recorded",
    "raw_prompt_recorded",
    "secret_fixture_used",
    "sensitive_fixture_used",
}
SECRET_VALUE_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.I),
    re.compile(r"\bsk-[A-Za-z0-9._-]{6,}\b", re.I),
]
ALLOWED_USAGE_KEYS = {
    "reported",
    "reason",
    "model",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "cached_tokens",
    "cost_usd",
    "latency_ms",
}


def validate(payload: dict[str, Any], *, allow_blocked: bool = False, coding_v1: bool = False) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    if payload.get("story_id") != STORY_ID:
        errors.append(f"story_id must be {STORY_ID}")
    _require_timestamp(payload.get("created_at"), "created_at", errors)

    result = payload.get("result")
    if result not in {"passed", "failed", "blocked"}:
        errors.append("result must be passed, failed, or blocked")
    if result == "blocked" and not allow_blocked:
        errors.append("blocked evidence records readiness/blockers only; rerun with live credentials to complete S017-002")
    if result in {"passed", "failed"}:
        errors.extend(placeholder_errors(payload))
        errors.extend(secret_leak_errors(payload))

    redaction = _dict(payload.get("redaction"))
    for key in ["api_key_recorded", "raw_file_id_recorded", "raw_prompt_recorded", "sensitive_fixture_used"]:
        if redaction.get(key) is not False:
            errors.append(f"redaction.{key} must be false")

    environment = _dict(payload.get("environment"))
    for key in ["DOGE_LIVE_KIMI", "MOONSHOT_API_KEY_PRESENT", "DOGE_LIVE_KIMI_AGENT_SDK", "general_model"]:
        if key not in environment:
            errors.append(f"environment.{key} is required")
    if result in {"passed", "failed"}:
        for key in ["DOGE_LIVE_KIMI", "MOONSHOT_API_KEY_PRESENT"]:
            if environment.get(key) is not True:
                errors.append(f"{result} evidence requires environment.{key}=true")

    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list):
        errors.append("scenarios must be a list")
        scenarios = []
    scenario_map = {
        item.get("name"): item
        for item in scenarios
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    scenario_names = set(scenario_map)
    unexpected = scenario_names - BASE_REQUIRED_SCENARIOS - OPTIONAL_SCENARIOS
    if unexpected:
        errors.append(f"unexpected scenarios: {', '.join(sorted(unexpected))}")

    if result == "blocked":
        blockers = payload.get("blockers")
        if not isinstance(blockers, list) or not blockers:
            errors.append("blocked evidence requires non-empty blockers")
        if scenarios:
            errors.append("blocked evidence must not include executed scenarios")

    if result == "passed":
        missing = BASE_REQUIRED_SCENARIOS - scenario_names
        if missing:
            errors.append(f"missing required scenarios: {', '.join(sorted(missing))}")
        for name in sorted(BASE_REQUIRED_SCENARIOS):
            scenario = _dict(scenario_map.get(name))
            if scenario.get("status") != "passed":
                errors.append(f"{name}: passed evidence requires status=passed")
        if coding_v1:
            errors.extend(_coding_v1_optional_errors(scenario_map))
        else:
            closure_errors = _full_closure_errors(scenario_map, environment)
            if closure_errors and allow_blocked:
                pass
            else:
                errors.extend(closure_errors)

    if result == "failed" and not (scenario_map or payload.get("error")):
        errors.append("failed evidence requires scenarios or a redacted error")

    for scenario in scenarios:
        if not isinstance(scenario, dict):
            errors.append("each scenario must be an object")
            continue
        _validate_scenario(scenario, errors)

    if _contains_secret(payload):
        errors.append("evidence appears to contain a bearer token, provider key, raw file id, or key-value secret")

    return errors


def _validate_scenario(scenario: dict[str, Any], errors: list[str]) -> None:
    name = scenario.get("name")
    status = scenario.get("status")
    if status not in {"passed", "failed", "skipped"}:
        errors.append(f"{name}: status must be passed, failed, or skipped")
    if name in BASE_REQUIRED_SCENARIOS:
        for key in ["model", "profile"]:
            if not isinstance(scenario.get(key), str) or not scenario[key].strip():
                errors.append(f"{name}: {key} is required")
        latency = scenario.get("latency_ms")
        if status == "passed" and not isinstance(latency, (int, float)):
            errors.append(f"{name}: latency_ms is required for passed scenario")
        if status == "passed":
            _validate_usage_summary(name, scenario.get("usage"), errors)
    if name == "files_upload":
        file_info = _dict(scenario.get("file"))
        file_id_hash = file_info.get("file_id_hash")
        if status == "passed" and (not isinstance(file_id_hash, str) or not file_id_hash.startswith("sha256:")):
            errors.append("files_upload: file.file_id_hash must be redacted as sha256:<prefix>")
        if status == "passed" and file_info.get("deleted") is not True:
            errors.append("files_upload: file.deleted must be true for passed scenario")
        if "file_id" in file_info:
            errors.append("files_upload: raw file_id must not be recorded")
    if name in OPTIONAL_SCENARIOS and status == "skipped" and not scenario.get("reason"):
        errors.append(f"{name}: skipped scenario requires reason")


def _coding_v1_optional_errors(scenario_map: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    scenario_names = set(scenario_map)
    missing = OPTIONAL_SCENARIOS - scenario_names
    if missing:
        errors.append(f"coding-v1: missing optional scenarios: {', '.join(sorted(missing))}")
    for name in sorted(OPTIONAL_SCENARIOS & scenario_names):
        scenario = _dict(scenario_map.get(name))
        status = scenario.get("status")
        if status not in {"passed", "skipped"}:
            errors.append(f"{name}: coding-v1 optional scenario must be passed or skipped")
        if status == "skipped" and not scenario.get("reason"):
            errors.append(f"{name}: coding-v1 skipped optional scenario requires reason")
    return errors


def _full_closure_errors(
    scenario_map: dict[str, dict[str, Any]],
    environment: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    scenario_names = set(scenario_map)
    missing = FULL_CLOSURE_SCENARIOS - scenario_names
    if missing:
        errors.append(f"missing full-closure scenarios: {', '.join(sorted(missing))}")
    for name in sorted(FULL_CLOSURE_SCENARIOS & scenario_names):
        scenario = _dict(scenario_map.get(name))
        if scenario.get("status") != "passed":
            errors.append(f"{name}: full closure requires status=passed")
    if environment.get("DOGE_LIVE_KIMI_AGENT_SDK") is not True:
        errors.append("passed evidence for full closure requires environment.DOGE_LIVE_KIMI_AGENT_SDK=true")
    if environment.get("kimi_agent_sdk_installed") is not True:
        errors.append("passed evidence for full closure requires environment.kimi_agent_sdk_installed=true")
    return errors


def _validate_usage_summary(name: Any, usage: Any, errors: list[str]) -> None:
    if not isinstance(usage, dict):
        errors.append(f"{name}: usage summary is required for passed scenario")
        return
    unexpected = set(usage) - ALLOWED_USAGE_KEYS
    if unexpected:
        errors.append(f"{name}: usage summary has unexpected keys: {', '.join(sorted(unexpected))}")
    if not isinstance(usage.get("reported"), bool):
        errors.append(f"{name}: usage.reported must be true or false")
    if usage.get("reported") is False and not isinstance(usage.get("reason"), str):
        errors.append(f"{name}: usage.reason is required when usage.reported=false")
    for key in ["prompt_tokens", "completion_tokens", "total_tokens", "cached_tokens"]:
        if key in usage and not isinstance(usage[key], int):
            errors.append(f"{name}: usage.{key} must be an integer")
    for key in ["cost_usd", "latency_ms"]:
        if key in usage and not isinstance(usage[key], (int, float)):
            errors.append(f"{name}: usage.{key} must be numeric")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _require_timestamp(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} is required")
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} must be ISO-8601")


def _contains_secret(payload: dict[str, Any]) -> bool:
    return _scan_secret(payload, path=())


def _scan_secret(value: Any, *, path: tuple[str, ...]) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            if _is_secret_key(key_text) and key_text not in ALLOWED_SECRET_KEYS and _has_secret_like_value(item):
                return True
            if key_text == "file_id":
                return True
            if _scan_secret(item, path=(*path, key_text)):
                return True
        return False
    if isinstance(value, list):
        return any(_scan_secret(item, path=path) for item in value)
    if isinstance(value, str):
        return any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS)
    return False


def _is_secret_key(key: str) -> bool:
    return bool(re.search(r"api[_-]?key|secret|password|token", key, re.I))


def _has_secret_like_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate S017-002 Kimi live smoke evidence JSON.")
    parser.add_argument("evidence", help="Path to Kimi live smoke evidence JSON.")
    parser.add_argument("--allow-blocked", action="store_true", help="Allow blocked evidence for readiness tracking.")
    parser.add_argument(
        "--coding-v1",
        action="store_true",
        help="Validate Kimi Coding v1 gate semantics: text + Vision required; Files + Agent SDK optional but documented.",
    )
    args = parser.parse_args(argv)

    path = Path(args.evidence)
    payload = json.loads(path.read_text(encoding="utf-8"))
    errors = validate(payload, allow_blocked=args.allow_blocked, coding_v1=args.coding_v1)
    result = {"path": str(path), "passed": not errors, "errors": errors}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
