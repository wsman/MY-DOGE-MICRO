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

    async def vision_ok():
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

    scenarios = await smoke._run_live_scenarios(include_agent_sdk=False)

    assert [item["name"] for item in scenarios] == ["text_k26", "files_upload", "vision_base64"]
    assert [item["status"] for item in scenarios] == ["passed", "failed", "passed"]
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
