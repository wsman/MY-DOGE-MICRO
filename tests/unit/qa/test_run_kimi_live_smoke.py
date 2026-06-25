import base64
from types import SimpleNamespace

import pytest

from scripts import run_kimi_live_smoke as smoke


@pytest.mark.asyncio
async def test_run_live_scenarios_preserves_partial_failures(monkeypatch):
    async def text_ok():
        return {
            "name": "text_k26",
            "status": "passed",
            "profile": "financial_research",
            "model": "kimi-k2.6",
            "latency_ms": 10.0,
            "usage": {"reported": False, "reason": "provider_usage_not_reported"},
        }

    def files_fail():
        raise RuntimeError("provider failed for file-abc123456789")

    captured: dict[str, object] = {}

    async def vision_ok(vision_image=None):
        captured["vision_image"] = vision_image
        return {
            "name": "vision_base64",
            "status": "passed",
            "profile": "vision_analysis",
            "model": "kimi-k2.6",
            "latency_ms": 20.0,
            "usage": {"reported": False, "reason": "provider_usage_not_reported"},
        }

    monkeypatch.setattr(smoke, "_scenario_text", text_ok)
    monkeypatch.setattr(smoke, "_scenario_files", files_fail)
    monkeypatch.setattr(smoke, "_scenario_vision", vision_ok)

    scenarios = await smoke._run_live_scenarios(include_agent_sdk=False, vision_image="fixture.jpg")

    assert [item["name"] for item in scenarios] == ["text_k26", "files_upload", "vision_base64"]
    assert [item["status"] for item in scenarios] == ["passed", "failed", "passed"]
    assert captured["vision_image"] == "fixture.jpg"
    failed = scenarios[1]
    assert failed["profile"] == "document_extract"
    assert failed["model"] == "kimi-k2.6"
    assert "file-abc123456789" not in failed["error"]
    assert "[REDACTED_FILE_ID]" in failed["error"]


def test_safe_error_redacts_common_live_provider_secret_shapes(monkeypatch):
    monkeypatch.setenv("MOONSHOT_API_KEY", "sk-test-secret-123456")

    error = smoke._safe_error(
        RuntimeError(
            "Authorization: Bearer abc.def.ghi; key=sk-test-secret-123456; "
            "debug=sk-other-secret-123456; file=file-live123456"
        )
    )

    assert "abc.def.ghi" not in error
    assert "sk-test-secret-123456" not in error
    assert "sk-other-secret-123456" not in error
    assert "file-live123456" not in error
    assert "Bearer [REDACTED]" in error
    assert "key=[REDACTED]" in error
    assert "[REDACTED_API_KEY]" in error
    assert "[REDACTED_FILE_ID]" in error


def test_load_vision_fixture_accepts_real_jpeg(tmp_path):
    image = tmp_path / "fixture.jpg"
    image_bytes = b"\xff\xd8\xff\xe0" + b"jpeg-smoke"
    image.write_bytes(image_bytes)

    fixture = smoke._load_vision_fixture(str(image))

    assert fixture["source"] == "operator_image"
    assert fixture["media_type"] == "image/jpeg"
    assert fixture["size_bytes"] == len(image_bytes)
    assert base64.b64decode(fixture["data"]) == image_bytes
    assert "operator-provided image" in fixture["prompt"]


def test_scenario_files_skips_when_configured_endpoint_has_no_files_api(monkeypatch):
    class UnsupportedFilesClient:
        supports_files_api = False

    monkeypatch.setattr(smoke, "KimiFilesClient", UnsupportedFilesClient)

    result = smoke._scenario_files()

    assert result["name"] == "files_upload"
    assert result["status"] == "skipped"
    assert "does not support the Files API" in result["reason"]


@pytest.mark.asyncio
async def test_run_does_not_pass_when_files_upload_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("DOGE_LIVE_KIMI", "1")
    monkeypatch.setenv("MOONSHOT_API_KEY", "sk-test-secret-123456")

    async def text_ok():
        return {
            "name": "text_k26",
            "status": "passed",
            "profile": "financial_research",
            "model": "kimi-k2.6",
            "latency_ms": 10.0,
            "usage": {"reported": False, "reason": "provider_usage_not_reported"},
        }

    def files_fail():
        raise RuntimeError("provider failed for file-abc123456789")

    async def vision_ok(vision_image=None):
        return {
            "name": "vision_base64",
            "status": "passed",
            "profile": "vision_analysis",
            "model": "kimi-k2.6",
            "latency_ms": 20.0,
            "usage": {"reported": False, "reason": "provider_usage_not_reported"},
        }

    monkeypatch.setattr(smoke, "_scenario_text", text_ok)
    monkeypatch.setattr(smoke, "_scenario_files", files_fail)
    monkeypatch.setattr(smoke, "_scenario_vision", vision_ok)

    evidence = await smoke._run(SimpleNamespace(
        output_dir=str(tmp_path),
        skip_agent_sdk=True,
        vision_image=None,
    ))

    assert evidence["result"] == "failed"
    statuses = {item["name"]: item["status"] for item in evidence["scenarios"]}
    assert statuses == {
        "text_k26": "passed",
        "files_upload": "failed",
        "vision_base64": "passed",
    }
