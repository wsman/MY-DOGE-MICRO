import copy
import json
from pathlib import Path
import subprocess
import sys

from scripts.validate_kimi_live_smoke_evidence import validate


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_PATH = ROOT / "production" / "qa" / "evidence" / "live" / "kimi-live-smoke-2026-06-22.json"


def _blocked() -> dict:
    payload = copy.deepcopy(json.loads(EVIDENCE_PATH.read_text(encoding="utf-8")))
    payload.update(
        {
            "result": "blocked",
            "blockers": ["DOGE_LIVE_KIMI=1", "MOONSHOT_API_KEY"],
            "environment": {
                **payload["environment"],
                "DOGE_LIVE_KIMI": False,
                "MOONSHOT_API_KEY_PRESENT": False,
                "DOGE_LIVE_KIMI_AGENT_SDK": False,
                "kimi_agent_sdk_installed": False,
            },
            "scenarios": [],
        }
    )
    return payload


def _passed() -> dict:
    payload = copy.deepcopy(_blocked())
    payload.update(
        {
            "result": "passed",
            "blockers": [],
            "environment": {
                **payload["environment"],
                "DOGE_LIVE_KIMI": True,
                "MOONSHOT_API_KEY_PRESENT": True,
                "DOGE_LIVE_KIMI_AGENT_SDK": True,
                "kimi_agent_sdk_installed": True,
            },
            "scenarios": [
                {
                    "name": "text_k26",
                    "status": "passed",
                    "profile": "financial_research",
                    "model": "kimi-k2.6",
                    "latency_ms": 120.5,
                    "event_count": 1,
                    "response_chars": 17,
                    "finish_reasons": ["stop"],
                    "usage": {
                        "reported": True,
                        "prompt_tokens": 10,
                        "completion_tokens": 6,
                        "total_tokens": 16,
                    },
                },
                {
                    "name": "files_upload",
                    "status": "passed",
                    "profile": "document_extract",
                    "model": "kimi-k2.6",
                    "latency_ms": 210.0,
                    "usage": {"reported": False, "reason": "files_upload_metadata_only"},
                    "file": {
                        "type": "text/plain",
                        "purpose": "file-extract",
                        "file_id_hash": "sha256:1234567890abcdef",
                        "deleted": True,
                    },
                    "metadata_keys": ["id", "purpose", "status"],
                },
                {
                    "name": "vision_base64",
                    "status": "passed",
                    "profile": "vision_analysis",
                    "model": "kimi-k2.6",
                    "latency_ms": 320.0,
                    "event_count": 1,
                    "response_chars": 12,
                    "finish_reasons": ["stop"],
                    "usage": {"reported": False, "reason": "provider_usage_not_reported"},
                },
                {
                    "name": "agent_sdk_optional",
                    "status": "passed",
                    "profile": "agent_automation",
                    "model": "kimi-k2.6",
                    "latency_ms": 155.0,
                    "event_count": 1,
                    "response_chars": 18,
                    "finish_reasons": ["stop"],
                    "usage": {"reported": False, "reason": "provider_usage_not_reported"},
                },
            ],
        }
    )
    return payload


def test_blocked_evidence_requires_explicit_allow_blocked():
    payload = _blocked()

    assert validate(payload, allow_blocked=True) == []
    errors = validate(payload)

    assert any("blocked evidence" in error for error in errors)


def test_passed_evidence_validates_when_required_scenarios_pass():
    assert validate(_passed()) == []


def test_passed_evidence_requires_files_upload_for_full_closure():
    payload = _passed()
    payload["scenarios"] = [item for item in payload["scenarios"] if item["name"] != "files_upload"]

    errors = validate(payload)

    assert any("missing full-closure scenarios" in error for error in errors)
    assert validate(payload, allow_blocked=True) == []


def test_current_partial_live_evidence_is_controlled_open_only():
    payload = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    strict_errors = validate(payload)

    assert any("files_upload: full closure requires status=passed" in error for error in strict_errors)
    assert any("agent_sdk_optional" in error for error in strict_errors)
    assert validate(payload, allow_blocked=True) == []


def test_passed_evidence_rejects_missing_required_scenario():
    payload = _passed()
    payload["scenarios"] = [item for item in payload["scenarios"] if item["name"] != "vision_base64"]

    errors = validate(payload)

    assert any("missing required scenarios" in error for error in errors)


def test_passed_evidence_requires_live_environment_gates():
    payload = _passed()
    payload["environment"]["MOONSHOT_API_KEY_PRESENT"] = False

    errors = validate(payload)

    assert any("passed evidence requires environment.MOONSHOT_API_KEY_PRESENT=true" in error for error in errors)


def test_files_upload_rejects_raw_file_id():
    payload = _passed()
    for scenario in payload["scenarios"]:
        if scenario["name"] == "files_upload":
            scenario["file"]["file_id"] = "file-raw-provider-id"

    errors = validate(payload)

    assert any("raw file id" in error.lower() for error in errors)


def test_files_upload_pass_requires_cleanup_confirmation():
    payload = _passed()
    for scenario in payload["scenarios"]:
        if scenario["name"] == "files_upload":
            scenario["file"]["deleted"] = False

    errors = validate(payload)

    assert any("files_upload: file.deleted must be true" in error for error in errors)


def test_optional_files_upload_skip_requires_reason():
    payload = _passed()
    for index, scenario in enumerate(payload["scenarios"]):
        if scenario["name"] == "files_upload":
            payload["scenarios"][index] = {"name": "files_upload", "status": "skipped"}

    errors = validate(payload)

    assert any("files_upload: skipped scenario requires reason" in error for error in errors)


def test_passed_required_scenario_requires_usage_summary():
    payload = _passed()
    for scenario in payload["scenarios"]:
        if scenario["name"] == "text_k26":
            scenario.pop("usage")

    errors = validate(payload)

    assert any("text_k26: usage summary is required" in error for error in errors)


def test_usage_summary_rejects_unexpected_provider_payload_keys():
    payload = _passed()
    for scenario in payload["scenarios"]:
        if scenario["name"] == "vision_base64":
            scenario["usage"]["raw_provider_payload"] = {"id": "provider-debug"}

    errors = validate(payload)

    assert any("vision_base64: usage summary has unexpected keys" in error for error in errors)


def test_secret_like_values_are_rejected_without_false_positive_for_present_flags():
    payload = _passed()

    assert validate(payload) == []

    payload["error"] = "debug Authorization: Bearer abc.def.ghi"
    errors = validate(payload)

    assert any("appears to contain" in error for error in errors)


def test_completed_evidence_rejects_unresolved_date_placeholder():
    payload = _passed()
    payload["created_at"] = "YYYY-MM-DDTHH:MM:SSZ"

    errors = validate(payload)

    assert any("unresolved placeholder: YYYY-MM-DDTHH:MM:SSZ" in error for error in errors)


def test_cli_allows_blocked_only_with_flag():
    script = ROOT / "scripts" / "validate_kimi_live_smoke_evidence.py"
    denied = subprocess.run(
        [sys.executable, str(script), str(EVIDENCE_PATH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    allowed = subprocess.run(
        [sys.executable, str(script), str(EVIDENCE_PATH), "--allow-blocked"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert denied.returncode == 1
    assert "full closure" in denied.stdout
    assert allowed.returncode == 0
    assert json.loads(allowed.stdout)["passed"] is True


def _coding_v1_passed():
    return {
        "schema": "doge.kimi_live_smoke.v1",
        "story_id": "S017-002",
        "created_at": "2026-06-29T00:00:00+00:00",
        "result": "passed",
        "gate": "coding-v1",
        "environment": {
            "DOGE_LIVE_KIMI": True,
            "MOONSHOT_API_KEY_PRESENT": True,
            "DOGE_LIVE_KIMI_AGENT_SDK": False,
            "kimi_agent_sdk_installed": False,
            "base_url": "https://api.moonshot.ai/v1",
            "general_model": "kimi-k2.6",
        },
        "redaction": {
            "api_key_recorded": False,
            "raw_file_id_recorded": False,
            "raw_prompt_recorded": False,
            "sensitive_fixture_used": False,
        },
        "scenarios": [
            {
                "name": "text_k26",
                "status": "passed",
                "profile": "financial_research",
                "model": "kimi-k2.6",
                "latency_ms": 120.5,
                "event_count": 1,
                "response_chars": 17,
                "finish_reasons": ["stop"],
                "usage": {
                    "reported": True,
                    "prompt_tokens": 10,
                    "completion_tokens": 6,
                    "total_tokens": 16,
                },
            },
            {
                "name": "files_upload",
                "status": "skipped",
                "profile": "document_extract",
                "model": "kimi-k2.6",
                "reason": "configured Kimi endpoint does not support the Files API",
                "usage": {"reported": False, "reason": "files_upload_optional_not_supported"},
            },
            {
                "name": "vision_base64",
                "status": "passed",
                "profile": "vision_analysis",
                "model": "kimi-k2.6",
                "latency_ms": 320.0,
                "event_count": 1,
                "response_chars": 12,
                "finish_reasons": ["stop"],
                "usage": {"reported": False, "reason": "provider_usage_not_reported"},
            },
            {
                "name": "agent_sdk_optional",
                "status": "skipped",
                "profile": "agent_automation",
                "model": "kimi-k2.6",
                "reason": "kimi_agent_sdk is not installed",
                "usage": {"reported": False, "reason": "agent_sdk_optional_not_installed"},
            },
        ],
    }


def test_coding_v1_passes_with_required_and_documented_optional():
    assert validate(_coding_v1_passed(), coding_v1=True) == []


def test_coding_v1_rejects_missing_optional_scenario():
    payload = _coding_v1_passed()
    payload["scenarios"] = [item for item in payload["scenarios"] if item["name"] != "agent_sdk_optional"]

    errors = validate(payload, coding_v1=True)

    assert any("missing optional scenarios" in error for error in errors)


def test_coding_v1_rejects_skipped_optional_without_reason():
    payload = _coding_v1_passed()
    for scenario in payload["scenarios"]:
        if scenario["name"] == "files_upload":
            scenario.pop("reason")

    errors = validate(payload, coding_v1=True)

    assert any("skipped optional scenario requires reason" in error for error in errors)


def test_coding_v1_fails_when_required_scenario_fails():
    payload = _coding_v1_passed()
    for scenario in payload["scenarios"]:
        if scenario["name"] == "text_k26":
            scenario["status"] = "failed"

    errors = validate(payload, coding_v1=True)

    assert any("text_k26: passed evidence requires status=passed" in error for error in errors)


def test_coding_v1_cli_flag():
    script = ROOT / "scripts" / "validate_kimi_live_smoke_evidence.py"
    coding_v1_path = ROOT / "production" / "qa" / "evidence" / "live" / "kimi-live-smoke-coding-v1-fixture.json"
    coding_v1_path.write_text(json.dumps(_coding_v1_passed()), encoding="utf-8")
    try:
        result = subprocess.run(
            [sys.executable, str(script), str(coding_v1_path), "--coding-v1"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert json.loads(result.stdout)["passed"] is True
    finally:
        coding_v1_path.unlink(missing_ok=True)
