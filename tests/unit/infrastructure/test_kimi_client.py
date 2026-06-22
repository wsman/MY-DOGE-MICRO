from types import SimpleNamespace

import pytest

from doge.config.settings import reset_settings
from doge.core.ports.agent_model import AgentContentPart, AgentMessage
from doge.infrastructure.llm.kimi_client import KimiAgentModel, KimiMessageSerializer


class _SecretProvider:
    def __init__(self, values):
        self.values = values

    def get_secret(self, name: str):
        return self.values.get(name)


@pytest.mark.asyncio
async def test_kimi_client_yields_nothing_without_api_key(monkeypatch):
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    reset_settings()

    events = [event async for event in KimiAgentModel().chat([AgentMessage(role="user", content="hi")])]

    assert events == []


@pytest.mark.asyncio
async def test_kimi_client_rejects_non_auto_tool_choice():
    with pytest.raises(ValueError):
        _ = [
            event
            async for event in KimiAgentModel(api_key="key").chat(
                [AgentMessage(role="user", content="hi")],
                tools=[{"type": "function", "function": {"name": "abc", "parameters": {"type": "object"}}}],
                tool_choice="required",
            )
        ]


@pytest.mark.asyncio
async def test_kimi_client_omits_temperature_and_sets_thinking(monkeypatch):
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            message = SimpleNamespace(
                role="assistant",
                content="memo",
                tool_calls=[],
            )
            choice = SimpleNamespace(message=message, finish_reason="stop")
            usage = SimpleNamespace(model_dump=lambda exclude_none=True: {"total_tokens": 7})
            return SimpleNamespace(
                choices=[choice],
                usage=usage,
                model_dump=lambda exclude_none=True: {"id": "resp-1"},
            )

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    import openai

    monkeypatch.setattr(openai, "AsyncOpenAI", FakeAsyncOpenAI)

    events = [
        event
        async for event in KimiAgentModel(
            api_key="moonshot-key",
            base_url="https://api.moonshot.ai/v1",
            model="kimi-k2.6",
        ).chat([AgentMessage(role="user", content="hi")], stream=False)
    ]

    assert len(events) == 1
    assert events[0].message.content == "memo"
    assert captured["client"]["api_key"] == "moonshot-key"
    assert captured["client"]["base_url"] == "https://api.moonshot.ai/v1"
    assert captured["model"] == "kimi-k2.6"
    assert "temperature" not in captured
    assert captured["extra_body"] == {"thinking": {"type": "enabled", "keep": "all"}}


@pytest.mark.asyncio
async def test_kimi_client_reads_api_key_from_secret_provider(monkeypatch):
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            message = SimpleNamespace(role="assistant", content="memo", tool_calls=[])
            choice = SimpleNamespace(message=message, finish_reason="stop")
            return SimpleNamespace(
                choices=[choice],
                usage=None,
                model_dump=lambda exclude_none=True: {"id": "resp-1"},
            )

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    import openai

    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    reset_settings()
    monkeypatch.setattr(openai, "AsyncOpenAI", FakeAsyncOpenAI)

    events = [
        event
        async for event in KimiAgentModel(
            secret_provider=_SecretProvider({"kimi.api_key": "provider-key"}),
            model="kimi-k2.6",
        ).chat([AgentMessage(role="user", content="hi")], stream=False)
    ]

    assert len(events) == 1
    assert captured["client"]["api_key"] == "provider-key"


@pytest.mark.asyncio
async def test_kimi_client_can_disable_thinking_per_call(monkeypatch):
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            message = SimpleNamespace(role="assistant", content="memo", tool_calls=[])
            choice = SimpleNamespace(message=message, finish_reason="stop")
            return SimpleNamespace(
                choices=[choice],
                usage=None,
                model_dump=lambda exclude_none=True: {"id": "resp-1"},
            )

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    import openai

    monkeypatch.setattr(openai, "AsyncOpenAI", FakeAsyncOpenAI)

    events = [
        event
        async for event in KimiAgentModel(api_key="moonshot-key", model="kimi-k2.6").chat(
            [AgentMessage(role="user", content="hi")],
            stream=False,
            thinking_enabled=False,
        )
    ]

    assert events[0].message.content == "memo"
    assert captured["extra_body"] == {"thinking": {"type": "disabled"}}


@pytest.mark.asyncio
async def test_kimi_client_rejects_non_thinking_k27_code():
    with pytest.raises(ValueError, match="does not support thinking_enabled=False"):
        _ = [
            event
            async for event in KimiAgentModel(api_key="moonshot-key").chat(
                [AgentMessage(role="user", content="hi")],
                model="kimi-k2.7-code",
                thinking_enabled=False,
            )
        ]


def test_kimi_serializer_maps_structured_image_content():
    payload = KimiMessageSerializer.serialize_messages([
        AgentMessage(
            role="user",
            content=[
                AgentContentPart.text_part("What trend do you see?"),
                AgentContentPart.image_base64(media_type="image/png", data="abc123"),
                AgentContentPart.image_file_id("file-vision-1"),
            ],
        )
    ])

    assert payload == [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What trend do you see?"},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64,abc123"},
                },
                {
                    "type": "image_url",
                    "image_url": {"url": "ms://file-vision-1"},
                },
            ],
        }
    ]


def test_kimi_serializer_maps_structured_video_content():
    payload = KimiMessageSerializer.serialize_messages([
        AgentMessage(
            role="user",
            content=[
                AgentContentPart.text_part("Summarize the clip."),
                AgentContentPart.video_file_id("file-video-1"),
            ],
        )
    ])

    assert payload == [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Summarize the clip."},
                {
                    "type": "video_url",
                    "video_url": {"url": "ms://file-video-1"},
                },
            ],
        }
    ]


def test_kimi_serializer_places_extracted_file_content_as_system_message():
    payload = KimiMessageSerializer.serialize_messages([
        AgentMessage(
            role="user",
            content=[
                AgentContentPart.file_text(text="extracted report text", filename="report.pdf", file_id="file-1"),
                AgentContentPart.text_part("Summarize the file."),
            ],
        )
    ])

    assert payload == [
        {"role": "system", "content": "extracted report text"},
        {"role": "user", "content": [{"type": "text", "text": "Summarize the file."}]},
    ]


@pytest.mark.asyncio
async def test_kimi_client_sends_serialized_multimodal_messages(monkeypatch):
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            message = SimpleNamespace(role="assistant", content="chart summary", tool_calls=[])
            choice = SimpleNamespace(message=message, finish_reason="stop")
            return SimpleNamespace(
                choices=[choice],
                usage=None,
                model_dump=lambda exclude_none=True: {"id": "resp-vision"},
            )

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    import openai

    monkeypatch.setattr(openai, "AsyncOpenAI", FakeAsyncOpenAI)

    events = [
        event
        async for event in KimiAgentModel(api_key="moonshot-key", model="kimi-k2.6").chat(
            [
                AgentMessage(
                    role="user",
                    content=[
                        AgentContentPart.text_part("Describe"),
                        AgentContentPart.image_file_id("file-vision-1"),
                    ],
                )
            ],
            stream=False,
        )
    ]

    assert events[0].message.content == "chart summary"
    assert captured["messages"][0]["content"][1]["image_url"]["url"] == "ms://file-vision-1"


@pytest.mark.asyncio
async def test_kimi_client_retries_rate_limited_create_then_yields(monkeypatch):
    attempts = {"count": 0}

    class FakeCompletions:
        async def create(self, **kwargs):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("HTTP 429 Too Many Requests")
            message = SimpleNamespace(role="assistant", content="recovered", tool_calls=[])
            choice = SimpleNamespace(message=message, finish_reason="stop")
            return SimpleNamespace(
                choices=[choice],
                usage=None,
                model_dump=lambda exclude_none=True: {"id": "resp-retry"},
            )

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    import openai

    monkeypatch.setattr(openai, "AsyncOpenAI", FakeAsyncOpenAI)

    events = [
        event
        async for event in KimiAgentModel(api_key="moonshot-key", max_retries=2, retry_delay=0).chat(
            [AgentMessage(role="user", content="hi")],
            stream=False,
        )
    ]

    assert attempts["count"] == 2
    assert events[0].message.content == "recovered"


@pytest.mark.asyncio
async def test_kimi_client_does_not_retry_non_retryable_create_error(monkeypatch):
    attempts = {"count": 0}

    class FakeCompletions:
        async def create(self, **kwargs):
            attempts["count"] += 1
            raise ValueError("bad request")

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    import openai

    monkeypatch.setattr(openai, "AsyncOpenAI", FakeAsyncOpenAI)

    events = [
        event
        async for event in KimiAgentModel(api_key="moonshot-key", max_retries=2, retry_delay=0).chat(
            [AgentMessage(role="user", content="hi")],
            stream=False,
        )
    ]

    assert attempts["count"] == 1
    assert events == []
