"""Runtime bootstrap container."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from doge.application import composition


@dataclass(frozen=True)
class RuntimeContainer:
    """Typed entry point for agent runtime wiring."""

    db_path: Path | str | None = None

    def build_research_agent_runtime(self, model: Any = None, tool_registry: Any = None):
        return composition.build_research_agent_runtime(model=model, tool_registry=tool_registry)

    def build_persisted_research_agent_runtime(
        self,
        model: Any = None,
        tool_registry: Any = None,
        event_publisher: Any = None,
    ):
        return composition.build_persisted_research_agent_runtime(
            model=model,
            tool_registry=tool_registry,
            event_publisher=event_publisher,
            db_path=self.db_path,
        )

    def build_event_subscriber(self, *, poll_interval_seconds: float = 0.1):
        return composition.build_event_subscriber(
            self.db_path,
            poll_interval_seconds=poll_interval_seconds,
        )

    def build_runtime_outbox_repository(self):
        return composition.build_runtime_outbox_repository(self.db_path)

    def build_agent_repositories(self):
        return composition.build_agent_repositories(self.db_path)

    def build_agent_document_repository(self):
        return composition.build_agent_document_repository(self.db_path)

    def build_agent_evidence_repository(self):
        return composition.build_agent_evidence_repository(self.db_path)

    def build_agent_run_queue(self):
        return composition.build_agent_run_queue(self.db_path)

    def build_agent_idempotency_store(self):
        return composition.build_agent_idempotency_store(self.db_path)

    def build_agent_unit_of_work(self, event_publisher: Any = None):
        return composition.build_agent_unit_of_work(self.db_path, event_publisher=event_publisher)

    def build_run_summary_use_case(self, runtime: Any = None, evidence_repository: Any = None):
        return composition.build_run_summary_use_case(
            runtime=runtime,
            evidence_repository=evidence_repository,
            db_path=self.db_path,
        )

    def build_capability_registry_use_case(self):
        return composition.build_capability_registry_use_case()

    def build_default_tool_registry(self, entitlement_checker: Any = None, context: Any = None):
        return composition.build_default_tool_registry(
            entitlement_checker=entitlement_checker,
            context=context,
            db_path=self.db_path,
        )

    def build_execute_run_use_case(self, model: Any = None, tool_registry: Any = None):
        return composition.build_execute_run_use_case(
            model=model,
            tool_registry=tool_registry,
            db_path=self.db_path,
        )

    def build_resume_run_use_case(self, model: Any = None, tool_registry: Any = None):
        return composition.build_resume_run_use_case(
            model=model,
            tool_registry=tool_registry,
            db_path=self.db_path,
        )


def build_runtime_container(db_path: Path | str | None = None) -> RuntimeContainer:
    """Build the runtime container."""

    return RuntimeContainer(db_path=db_path)
