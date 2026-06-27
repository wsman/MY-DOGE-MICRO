"""Architecture guard for runtime streaming semantics.

Per ADR-0025, the streaming contract is:
- list_events = synchronous persisted query
- stream_events = replay-only async iterator
- live SSE = RunStreamHandler + IEventSubscriber.subscribe

These tests assert the documented contracts by inspecting source code.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_v1_run_stream_uses_run_stream_handler() -> None:
    source = (
        PROJECT_ROOT
        / "src"
        / "doge"
        / "interfaces"
        / "api"
        / "routers"
        / "v1"
        / "run_stream.py"
    ).read_text(encoding="utf-8")

    assert "RunStreamHandler" in source
    assert "from doge.interfaces.api.handlers import" in source
    assert "RunStreamHandler(runtime=runtime, subscriber=subscriber)" in source


def test_v1_run_stream_does_not_call_runtime_stream_events() -> None:
    source = (
        PROJECT_ROOT
        / "src"
        / "doge"
        / "interfaces"
        / "api"
        / "routers"
        / "v1"
        / "run_stream.py"
    ).read_text(encoding="utf-8")

    assert "runtime.stream_events" not in source


def test_v1_run_stream_uses_list_events_for_replay() -> None:
    handler_source = (
        PROJECT_ROOT
        / "src"
        / "doge"
        / "interfaces"
        / "api"
        / "handlers"
        / "streaming.py"
    ).read_text(encoding="utf-8")

    assert "self._runtime.list_events" in handler_source
    assert "self._subscriber.subscribe" in handler_source


def test_legacy_api_stream_events_is_replay_only_and_documented() -> None:
    source = (
        PROJECT_ROOT
        / "src"
        / "doge"
        / "interfaces"
        / "api"
        / "routers"
        / "agent.py"
    ).read_text(encoding="utf-8")

    # Legacy route is the only production caller of runtime.stream_events().
    assert "runtime.stream_events(" in source
    # It must be documented as a compatibility surface.
    assert "legacy" in source.lower() or "compatibility" in source.lower()


def test_core_port_stream_events_documented_as_replay_only() -> None:
    source = (
        PROJECT_ROOT / "src" / "doge" / "core" / "ports" / "agent_runtime.py"
    ).read_text(encoding="utf-8")

    assert "stream_events" in source
    # The docstring must warn that the default contract is replay-only.
    assert "replay" in source.lower()


def test_persisted_runtime_stream_events_is_replay_only() -> None:
    source = (
        PROJECT_ROOT
        / "src"
        / "doge"
        / "infrastructure"
        / "agent"
        / "persisted_runtime.py"
    ).read_text(encoding="utf-8")

    stream_method_start = source.find("async def stream_events")
    assert stream_method_start != -1
    method_body = source[stream_method_start : source.find("async def resolve_approval", stream_method_start)]
    assert "replay" in method_body.lower() or "list_events" in method_body
    assert "subscriber" not in method_body
    assert "poll" not in method_body


def test_v1_run_stream_module_docstring_mentions_adr0025() -> None:
    """The v1 run_stream module docstring should reference ADR-0025 semantics."""
    source = (
        PROJECT_ROOT
        / "src"
        / "doge"
        / "interfaces"
        / "api"
        / "routers"
        / "v1"
        / "run_stream.py"
    ).read_text(encoding="utf-8")

    # Module docstring should explain the three streaming concepts
    assert "list_events" in source.lower()
    assert "stream_events" in source.lower()
    assert "RunStreamHandler" in source


def test_core_port_list_events_documented_as_canonical_query() -> None:
    """list_events docstring should direct consumers to RunStreamHandler for live streaming."""
    source = (
        PROJECT_ROOT / "src" / "doge" / "core" / "ports" / "agent_runtime.py"
    ).read_text(encoding="utf-8")

    list_events_start = source.find("def list_events")
    assert list_events_start != -1
    method_body = source[list_events_start : source.find("def list_artifacts", list_events_start)]
    # Should mention that live streaming uses RunStreamHandler / IEventSubscriber
    assert "runstreamhandler" in method_body.lower() or "subscriber" in method_body.lower() or "live" in method_body.lower()


def test_outbox_publisher_docstring_notes_feature_flag() -> None:
    """The outbox publisher docstring should note the feature-flag gating."""
    source = (
        PROJECT_ROOT
        / "src"
        / "doge"
        / "application"
        / "agent"
        / "outbox_publisher.py"
    ).read_text(encoding="utf-8")

    assert "feature flag" in source.lower() or "feature_flag" in source.lower()
    assert "no-op" in source.lower() or "off" in source.lower() or "not active" in source.lower()
