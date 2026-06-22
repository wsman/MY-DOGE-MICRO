"""Opt-in live Kimi smoke tests for Sprint 016 closure.

These tests are skipped by default. They only run when the operator explicitly
sets DOGE_LIVE_KIMI=1 and provides MOONSHOT_API_KEY. They are intentionally
small and use non-sensitive generated fixtures.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

import pytest

from doge.config.settings import reset_settings
from doge.core.ports.agent_model import AgentContentPart, AgentMessage
from doge.infrastructure.agent.backends import KimiAgentSdkBackend
from doge.infrastructure.llm.kimi_client import KimiAgentModel
from doge.infrastructure.llm.kimi_files_client import KimiFilesClient


_TINY_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAIAAAACUFjqAAAAGUlEQVR4nGP8z8AARLJgwiM3"
    "LqkEAC8iAhE7A52jAAAAAElFTkSuQmCC"
)


def _require_live_kimi() -> str:
    if os.environ.get("DOGE_LIVE_KIMI") != "1":
        pytest.skip("set DOGE_LIVE_KIMI=1 to run live Kimi smoke tests")
    api_key = os.environ.get("MOONSHOT_API_KEY")
    if not api_key:
        pytest.skip("MOONSHOT_API_KEY is required for live Kimi smoke tests")
    reset_settings()
    return api_key


@pytest.mark.asyncio
async def test_live_kimi_text_k26_smoke():
    _require_live_kimi()
    model = KimiAgentModel(model=os.environ.get("KIMI_GENERAL_MODEL") or "kimi-k2.6", max_retries=0)

    events = [
        event
        async for event in model.chat(
            [AgentMessage(role="user", content="Return exactly: S017_KIMI_TEXT_OK")],
            stream=False,
            max_tokens=64,
            request_metadata={"smoke": "s017_live_text"},
        )
    ]

    assert events, "live Kimi text smoke returned no events"
    combined = "".join(event.message.content for event in events)
    assert combined.strip() or any(event.finish_reason for event in events)


def test_live_kimi_files_upload_smoke(tmp_path: Path):
    _require_live_kimi()
    source = tmp_path / "s017-nonsensitive-smoke.txt"
    source.write_text("S017 Kimi Files smoke fixture. Non-sensitive synthetic text.", encoding="utf-8")
    client = KimiFilesClient()

    file_id = client.upload_file(source, purpose="file-extract")
    try:
        assert file_id
        info = client.get_file_info(file_id)
        assert isinstance(info, dict)
    finally:
        try:
            client.delete_file(file_id)
        except Exception:
            pass


@pytest.mark.asyncio
async def test_live_kimi_vision_base64_smoke():
    _require_live_kimi()
    assert base64.b64decode(_TINY_PNG_BASE64)
    model = KimiAgentModel(model=os.environ.get("KIMI_GENERAL_MODEL") or "kimi-k2.6", max_retries=0)

    events = [
        event
        async for event in model.chat(
            [
                AgentMessage(
                    role="user",
                    content=[
                        AgentContentPart.text_part(
                            "This is a tiny generated chart-like PNG smoke fixture. "
                            "Reply with a short confirmation."
                        ),
                        AgentContentPart.image_base64(media_type="image/png", data=_TINY_PNG_BASE64),
                    ],
                )
            ],
            stream=False,
            max_tokens=96,
            request_metadata={"smoke": "s016_live_vision"},
        )
    ]

    assert events, "live Kimi vision smoke returned no events"
    combined = "".join(event.message.content for event in events)
    assert combined.strip() or any(event.finish_reason for event in events)


@pytest.mark.asyncio
async def test_live_kimi_agent_sdk_optional_smoke():
    _require_live_kimi()
    if os.environ.get("DOGE_LIVE_KIMI_AGENT_SDK") != "1":
        pytest.skip("set DOGE_LIVE_KIMI_AGENT_SDK=1 to run optional Agent SDK smoke")
    pytest.importorskip("kimi_agent_sdk")
    backend = KimiAgentSdkBackend(
        api_key=os.environ.get("MOONSHOT_API_KEY"),
        base_url=os.environ.get("KIMI_BASE_URL") or "https://api.moonshot.ai/v1",
        model=os.environ.get("KIMI_GENERAL_MODEL") or "kimi-k2.6",
    )
    tools = [{
        "type": "function",
        "function": {
            "name": "lookup_evidence",
            "description": "Synthetic smoke tool schema; the model does not need to call it.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
        },
    }]

    events = [
        event
        async for event in backend.chat(
            [AgentMessage(role="user", content="Reply with S017_AGENT_SDK_OK.")],
            tools=tools,
            tool_choice="auto",
            max_tokens=96,
            request_metadata={"session_id": "s017-live-smoke", "smoke": "s017_live_agent_sdk"},
            prompt_cache_key="s017-live-smoke",
        )
    ]

    assert events, "live Kimi Agent SDK smoke returned no events"
