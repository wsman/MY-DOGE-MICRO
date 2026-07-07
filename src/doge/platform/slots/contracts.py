"""Slot platform contracts: interfaces and the controlled ``SlotContext`` facade.

A slot (:class:`ISlot`) declares a :class:`~doge.platform.slots.manifest.SlotManifest`
and resolves its :class:`SlotContribution` against a :class:`SlotContext`.

``SlotContext`` is a deliberately narrow facade: it exposes settings (untyped),
a resolved feature-flag map, an optional tool-execution service, and optional
audit / permission / service-locator hooks. It must NEVER expose ``AppContainer``,
``RuntimeContainer`` or any bootstrap/infrastructure graph. ``settings`` is
``Any`` so this package does not import :mod:`doge.config`.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Optional, Protocol

from doge.core.domain.tool_descriptor import ToolDescriptor
from doge.platform.slots.errors import SlotConfigurationError
from doge.platform.slots.facets import (
    DataSourceContribution,
    DocumentParserContribution,
    EvalSuiteContribution,
    GatewayRouteContribution,
    GovernancePolicyContribution,
    ModelBackendContribution,
    UIPanelContribution,
    WatcherContribution,
    WorkflowTemplateContribution,
)
from doge.platform.slots.manifest import SlotHealth, SlotManifest

SLOT_SERVICE_SECRET_PROVIDER = "secret_provider"
SLOT_SERVICE_AGENT_BACKEND_REGISTRY = "agent_backend_registry"
SLOT_SERVICE_PLATFORM_REPOSITORY = "platform_repository"
SLOT_SERVICE_DATA_SOURCE_REGISTRY = "data_source_registry"
SLOT_SERVICE_DOCUMENT_PARSER_REGISTRY = "document_parser_registry"
SLOT_SERVICE_FASTAPI_APP = "fastapi_app"
SLOT_SERVICE_EVENT_BUS = "event_bus"
SLOT_SERVICE_GOVERNANCE_REPOSITORY = "governance_repository"


class ToolServiceProtocol(Protocol):
    """Minimal structural type for the tool-execution facade a slot resolves against.

    Contribution executors remain ``Any`` because the existing
    :meth:`ToolRegistry.include_descriptors` seam resolves descriptor methods by
    name; the slot layer only needs the descriptor accessor at resolve time.
    """

    def tool_descriptors(self) -> tuple[ToolDescriptor, ...]: ...


class SlotStatus(str, Enum):
    """Lifecycle status of a registered slot, as reported by :class:`SlotRegistry`."""

    REGISTERED = "registered"
    RESOLVED = "resolved"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass(frozen=True)
class SlotContribution:
    """Resolved contribution from a slot.

    ``executor`` is typed ``Any`` so :mod:`doge.platform.slots` does not import
    :mod:`doge.application.tools`; the bootstrap layer guarantees the executor's
    attributes match each tool descriptor's ``method_name`` when ``tools`` are
    populated.
    """

    slot_id: str
    tools: tuple[ToolDescriptor, ...] = ()
    executor: Any = None
    capabilities: tuple[Mapping[str, Any], ...] = ()
    model_backends: tuple[ModelBackendContribution, ...] = ()
    workflows: tuple[WorkflowTemplateContribution, ...] = ()
    data_sources: tuple[DataSourceContribution, ...] = ()
    document_parsers: tuple[DocumentParserContribution, ...] = ()
    routes: tuple[GatewayRouteContribution, ...] = ()
    ui_panels: tuple[UIPanelContribution, ...] = ()
    watchers: tuple[WatcherContribution, ...] = ()
    eval_suites: tuple[EvalSuiteContribution, ...] = ()
    governance_policies: tuple[GovernancePolicyContribution, ...] = ()


class ISlot(abc.ABC):
    """A unit of platform capability contribution."""

    @abc.abstractmethod
    def manifest(self) -> SlotManifest:
        """Return this slot's declarative manifest."""

    @abc.abstractmethod
    def resolve(self, context: "SlotContext") -> SlotContribution:
        """Resolve this slot's contribution against the controlled context."""

    def health(self, context: "SlotContext") -> SlotHealth:
        """Default health is the manifest's static health descriptor (overridable)."""
        return self.manifest().health

    def start(self, context: "SlotContext") -> None:
        """Optional lifecycle hook for slots with resources."""

    def stop(self, context: "SlotContext") -> None:
        """Optional lifecycle hook for slots with resources."""


class SlotContext:
    """Controlled, narrow service surface exposed to ``ISlot.resolve``.

    Uses ``__slots__`` so no ``__dict__`` (and therefore no incidental
    ``app_container``/``runtime_container``/``bootstrap``/``infrastructure``
    attributes) can leak to slot implementations.
    """

    __slots__ = (
        "_settings",
        "_feature_flags",
        "_tool_application_service",
        "_audit",
        "_permission_checker",
        "_service_locator",
    )

    def __init__(
        self,
        *,
        settings: Any,
        feature_flags: Mapping[str, bool],
        tool_application_service: ToolServiceProtocol | None = None,
        audit: Any = None,
        permission_checker: Any = None,
        service_locator: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self._settings = settings
        self._feature_flags = dict(feature_flags)
        self._tool_application_service = tool_application_service
        self._audit = audit
        self._permission_checker = permission_checker
        self._service_locator = service_locator

    @property
    def settings(self) -> Any:
        return self._settings

    @property
    def feature_flags(self) -> Mapping[str, bool]:
        return self._feature_flags

    @property
    def tool_application_service(self) -> ToolServiceProtocol | None:
        return self._tool_application_service

    @property
    def audit(self) -> Any:
        return self._audit

    @property
    def permission_checker(self) -> Any:
        return self._permission_checker

    def locate(self, service_id: str) -> Any:
        """Resolve a named service via the configured locator.

        Raises :class:`~doge.platform.slots.errors.SlotConfigurationError` when no
        locator is configured or the locator cannot return the named service.
        """
        if self._service_locator is None:
            raise SlotConfigurationError(
                f"no service locator configured; cannot resolve service {service_id!r}"
            )
        try:
            value = self._service_locator(service_id)
        except Exception as exc:  # locator failure must surface as a safe slot error
            raise SlotConfigurationError(
                f"service locator could not resolve {service_id!r}: {exc}"
            ) from exc
        if value is None:
            raise SlotConfigurationError(
                f"service locator returned no value for {service_id!r}"
            )
        return value
