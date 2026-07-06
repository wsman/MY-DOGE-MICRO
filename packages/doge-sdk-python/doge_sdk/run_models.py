"""Dict-compatible typed models for run REST responses."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast


ModelT = TypeVar("ModelT", bound="DogeDict")


class DogeDict(dict):
    """Base mapping that preserves plain-dict behavior with typed accessors."""

    def __init__(self, payload: Mapping[str, Any]) -> None:
        super().__init__(dict(payload))


def _wrap_model_list(value: Any, model_type: type[ModelT]) -> list[ModelT]:
    if not isinstance(value, list):
        return []
    wrapped: list[Any] = []
    for item in value:
        if isinstance(item, model_type):
            wrapped.append(item)
        elif isinstance(item, Mapping):
            wrapped.append(model_type(item))
        else:
            wrapped.append(item)
    return cast(list[ModelT], wrapped)


def _stored_model_list(value: Any, model_type: type[ModelT]) -> list[ModelT]:
    if not isinstance(value, list):
        return []
    return cast(list[ModelT], value)


def _dict_or_empty(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _string_list_or_empty(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


class RunEvent(DogeDict):
    @property
    def event_id(self) -> str | None:
        return self.get("event_id")

    @property
    def run_id(self) -> str | None:
        return self.get("run_id")

    @property
    def event_type(self) -> str | None:
        return self.get("event_type")

    @property
    def payload(self) -> dict[str, Any]:
        return _dict_or_empty(self.get("payload"))

    @property
    def sequence(self) -> int | None:
        return self.get("sequence")

    @property
    def schema_version(self) -> str | None:
        return self.get("schema_version")

    @property
    def created_at(self) -> str | None:
        return self.get("created_at")


class Artifact(DogeDict):
    @property
    def artifact_id(self) -> str | None:
        return self.get("artifact_id")

    @property
    def kind(self) -> str | None:
        return self.get("kind")

    @property
    def title(self) -> str | None:
        return self.get("title")

    @property
    def content(self) -> str | None:
        return self.get("content")

    @property
    def run_id(self) -> str | None:
        return self.get("run_id")

    @property
    def data(self) -> dict[str, Any]:
        return _dict_or_empty(self.get("data"))

    @property
    def created_at(self) -> str | None:
        return self.get("created_at")


class Approval(DogeDict):
    @property
    def approval_id(self) -> str | None:
        return self.get("approval_id")

    @property
    def action(self) -> str | None:
        return self.get("action")

    @property
    def risk_level(self) -> str | None:
        return self.get("risk_level")

    @property
    def run_id(self) -> str | None:
        return self.get("run_id")

    @property
    def status(self) -> str | None:
        return self.get("status")

    @property
    def created_at(self) -> str | None:
        return self.get("created_at")

    @property
    def resolved_at(self) -> str | None:
        return self.get("resolved_at")

    @property
    def why_needed(self) -> str | None:
        return self.get("why_needed")

    @property
    def impact(self) -> str | None:
        return self.get("impact")

    @property
    def deny_consequence(self) -> str | None:
        return self.get("deny_consequence")

    @property
    def publish_target(self) -> str | None:
        return self.get("publish_target")


class Run(DogeDict):
    def __init__(self, payload: Mapping[str, Any]) -> None:
        data = dict(payload)
        if isinstance(data.get("events"), list):
            data["events"] = _wrap_model_list(data.get("events"), RunEvent)
        if isinstance(data.get("artifacts"), list):
            data["artifacts"] = _wrap_model_list(data.get("artifacts"), Artifact)
        if isinstance(data.get("approvals"), list):
            data["approvals"] = _wrap_model_list(data.get("approvals"), Approval)
        super().__init__(data)

    @property
    def run_id(self) -> str | None:
        return self.get("run_id")

    @property
    def workflow(self) -> str | None:
        return self.get("workflow")

    @property
    def question(self) -> str | None:
        return self.get("question")

    @property
    def session_id(self) -> str | None:
        return self.get("session_id")

    @property
    def market(self) -> str | None:
        return self.get("market")

    @property
    def language(self) -> str | None:
        return self.get("language")

    @property
    def document_ids(self) -> list[str]:
        return _string_list_or_empty(self.get("document_ids"))

    @property
    def portfolio_id(self) -> str | None:
        return self.get("portfolio_id")

    @property
    def model_policy(self) -> dict[str, Any]:
        return _dict_or_empty(self.get("model_policy"))

    @property
    def workflow_context(self) -> Any | None:
        return self.get("workflow_context")

    @property
    def identity_snapshot(self) -> Any | None:
        return self.get("identity_snapshot")

    @property
    def status(self) -> str | None:
        return self.get("status")

    @property
    def events(self) -> list[RunEvent]:
        return _stored_model_list(self.get("events"), RunEvent)

    @property
    def artifacts(self) -> list[Artifact]:
        return _stored_model_list(self.get("artifacts"), Artifact)

    @property
    def approvals(self) -> list[Approval]:
        return _stored_model_list(self.get("approvals"), Approval)

    @property
    def cancel_requested_at(self) -> str | None:
        return self.get("cancel_requested_at")

    @property
    def schema_version(self) -> str | None:
        return self.get("schema_version")

    @property
    def created_at(self) -> str | None:
        return self.get("created_at")

    @property
    def updated_at(self) -> str | None:
        return self.get("updated_at")


class RunListItem(DogeDict):
    @property
    def run_id(self) -> str | None:
        return self.get("run_id")

    @property
    def workflow(self) -> str | None:
        return self.get("workflow")

    @property
    def question(self) -> str | None:
        return self.get("question")

    @property
    def session_id(self) -> str | None:
        return self.get("session_id")

    @property
    def market(self) -> str | None:
        return self.get("market")

    @property
    def language(self) -> str | None:
        return self.get("language")

    @property
    def portfolio_id(self) -> str | None:
        return self.get("portfolio_id")

    @property
    def status(self) -> str | None:
        return self.get("status")

    @property
    def event_count(self) -> int | None:
        return self.get("event_count")

    @property
    def artifact_count(self) -> int | None:
        return self.get("artifact_count")

    @property
    def approval_count(self) -> int | None:
        return self.get("approval_count")

    @property
    def created_at(self) -> str | None:
        return self.get("created_at")

    @property
    def updated_at(self) -> str | None:
        return self.get("updated_at")
