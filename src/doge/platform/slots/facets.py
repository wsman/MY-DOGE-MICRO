"""Slot contribution facet dataclasses.

These types describe resolve-time contributions without importing framework,
infrastructure, adapter, product, bootstrap, or interface modules. Runtime wiring
layers decide how to consume each facet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Mapping

if TYPE_CHECKING:
    from doge.platform.slots.contracts import SlotContext


@dataclass(frozen=True)
class ModelBackendContribution:
    """A model backend factory contributed by a slot."""

    backend_id: str
    factory: Callable[["SlotContext"], Any]
    capabilities: tuple[str, ...] = ()
    profiles: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowTemplateContribution:
    """A workflow template factory contributed by a slot."""

    slug: str
    template_factory: Callable[["SlotContext"], Mapping[str, Any]]
    capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class DataSourceContribution:
    """A data-source factory contributed by a slot."""

    source_id: str
    factory: Callable[["SlotContext"], Any]
    markets: tuple[str, ...]
    metadata_port: bool = False
    capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class DocumentParserContribution:
    """A document parser factory contributed by a slot."""

    parser_id: str
    factory: Callable[["SlotContext"], Any]
    supported_suffixes: tuple[str, ...]
    mime_types: tuple[str, ...] = ()
    priority: int = 0


@dataclass(frozen=True)
class GatewayRouteContribution:
    """A gateway route factory contributed by a slot."""

    router_id: str
    router_factory: Callable[["SlotContext"], Any]
    prefix: str
    tags: tuple[str, ...] = ()
    requires_auth: bool = True


@dataclass(frozen=True)
class UIPanelContribution:
    """A frontend panel descriptor contributed by a slot."""

    panel_id: str
    zone: str
    component_module: str
    order: int = 0
    modes: tuple[str, ...] = ()
    required_artifact_fields: tuple[str, ...] = ()
    label: str | None = None


@dataclass(frozen=True)
class WatcherDecision:
    """Decision returned by a watcher contribution."""

    action: str
    reason: str = ""
    approval_required: bool = False


@dataclass(frozen=True)
class WatcherContribution:
    """A runtime event watcher contributed by a slot."""

    watcher_id: str
    on_event: Callable[[Any, "SlotContext"], WatcherDecision]
    event_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvalSuiteContribution:
    """An eval suite contributed by a slot."""

    suite_id: str
    gold_set_path: str
    metrics: tuple[Callable[..., Any], ...] = ()
    execution_profile: str | None = None
    eval_policy: tuple[str, ...] = ()


@dataclass(frozen=True)
class GovernancePolicyContribution:
    """A governance policy contributed by a slot."""

    policy_id: str
    kind: str
    payload: Mapping[str, Any]
    entitlement_checker_factory: Callable[["SlotContext"], Any] | None = None
