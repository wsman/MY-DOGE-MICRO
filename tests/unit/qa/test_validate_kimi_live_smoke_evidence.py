import copy
import json
from pathlib import Path
import subprocess
import sys

from scripts.validate_kimi_live_smoke_evidence import validate


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_PATH = ROOT / "production" / "qa" / "evidence" / "live" / "kimi-live-smoke-2026-06-22.json"


def _blocked() -> dict:
    return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))


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
                    "usage": {"prompt_tokens": 10, "completion_tokens": 6, "total_tokens": 16},
                },
                {
                    "name": "files_upload",
                    "status": "passed",
                    "profile": "document_extract",
                    "model": "kimi-k2.6",
                    "latency_ms": 210.0,
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
                    "usage": {},
                },
                {
                    "name": "agent_sdk_optional",
                    "status": "skipped",
                    "reason": "kimi_agent_sdk is not installed",
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


def test_passed_evidence_rejects_missing_required_scenario():
    payload = _passed()
    payload["scenarios"] = [item for item in payload["scenarios"] if item["name"] != "vision_base64"]

    errors = validate(payload)

    assert any("missing required scenarios" in error for error in errors)


def test_files_upload_rejects_raw_file_id():
    payload = _passed()
    for scenario in payload["scenarios"]:
        if scenario["name"] == "files_upload":
            scenario["file"]["file_id"] = "file-raw-provider-id"

    errors = validate(payload)

    assert any("raw file id" in error.lower() for error in errors)


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
    assert "blocked evidence" in denied.stdout
    assert allowed.returncode == 0
    assert json.loads(allowed.stdout)["passed"] is True
