"""Unit tests for ArtifactFinalizer."""

from __future__ import annotations

import pytest

from doge.application.agent.artifact_finalizer import ArtifactFinalizer
from doge.core.domain.agent_models import AgentArtifact, AgentEvent, AgentRun, EventType
from doge.core.domain.run_execution_context import RunExecutionContext
from doge.core.ports.runtime_services import IArtifactEvaluationService


class FakeEvaluationService(IArtifactEvaluationService):
    def artifact_content(self, content: str | None) -> str:
        return content or ""

    def metrics(self, artifact_text: str, events: list[AgentEvent]) -> dict:
        return {"word_count": len(artifact_text.split()), "event_count": len(events)}


@pytest.fixture
def evaluation_service():
    return FakeEvaluationService()


@pytest.fixture
def artifact_finalizer(evaluation_service):
    return ArtifactFinalizer(evaluation_service=evaluation_service)


@pytest.fixture
def run():
    return AgentRun.create(workflow="test", question="Q")


@pytest.fixture
def events(run):
    return [
        AgentEvent(
            event_id="evt-1",
            run_id=run.run_id,
            event_type=EventType.RUN_CREATED,
            payload={},
            sequence=1,
        ),
    ]


def test_artifact_finalizer_build_artifact_returns_agent_artifact(artifact_finalizer, run, events):
    artifact = artifact_finalizer.build_artifact(run, "memo content", events)

    assert isinstance(artifact, AgentArtifact)
    assert artifact.kind == "investment_memo"
    assert artifact.title == "Investment Committee Memo"
    assert artifact.content == "memo content"
    assert artifact.run_id == run.run_id


def test_artifact_finalizer_build_artifact_includes_evaluation_metrics(artifact_finalizer, run, events):
    artifact = artifact_finalizer.build_artifact(run, "some memo text here", events)

    assert artifact.data["word_count"] == 4
    assert artifact.data["event_count"] == 1


def test_artifact_finalizer_build_artifact_includes_usage(artifact_finalizer, run, events):
    usage = {"prompt_tokens": 100, "completion_tokens": 50}
    artifact = artifact_finalizer.build_artifact(run, "content", events, usage=usage)

    assert artifact.data["usage"] == usage


def test_artifact_finalizer_build_artifact_with_none_content(artifact_finalizer, run, events):
    artifact = artifact_finalizer.build_artifact(run, None, events)

    assert artifact.content == ""


def test_artifact_finalizer_execution_context_returns_run_execution_context(artifact_finalizer, run):
    ctx = artifact_finalizer.execution_context(run)

    assert isinstance(ctx, RunExecutionContext)
