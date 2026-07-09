"""Default platform capability providers."""

from __future__ import annotations

import os
import re
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from doge.config import Settings
from doge.config.settings import FEATURE_LIFECYCLES
from doge.core.domain.tool_descriptor import ToolDescriptor

if TYPE_CHECKING:
    from doge.application.tools import ToolRegistry


class ToolExecutionProviderRegistry:
    """Dispatch table for provider-backed deterministic tool execution."""

    def __init__(self, providers: list[Any]) -> None:
        self._providers = tuple(providers)
        self._methods: dict[str, Any] = {}
        for provider in self._providers:
            for method_name, method in provider.tool_methods().items():
                if method_name in self._methods:
                    raise ValueError(f"Duplicate tool execution provider method: {method_name}")
                self._methods[method_name] = method

    def execute(self, method_name: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if method_name not in self._methods:
            raise RuntimeError(f"Tool execution provider not configured: {method_name}")
        return self._methods[method_name](*args, **kwargs)

    def method_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._methods))

    def tool_descriptors(self) -> tuple[ToolDescriptor, ...]:
        descriptors: list[ToolDescriptor] = []
        names: set[str] = set()
        for provider in self._providers:
            for descriptor in getattr(provider, "tool_descriptors", lambda: ())():
                if descriptor.name in names:
                    raise ValueError(f"Duplicate tool descriptor: {descriptor.name}")
                if descriptor.name not in self._methods:
                    raise ValueError(f"Tool descriptor has no execution method: {descriptor.name}")
                names.add(descriptor.name)
                descriptors.append(descriptor)
        return tuple(descriptors)


class FeatureCapabilityProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def collect(self, context: Any = None) -> list[dict[str, Any]]:
        return [
            capability(
                "feature.run_summary_api",
                "ui",
                "Run Summary API",
                _feature_status(self._settings.features.run_summary_api),
                metadata=_feature_metadata("run_summary_api"),
            ),
            capability(
                "feature.platform_objects",
                "ui",
                "Platform Objects",
                _feature_status(self._settings.features.platform_objects),
                metadata=_feature_metadata("platform_objects"),
            ),
            capability(
                "feature.workflow_templates",
                "workflow",
                "Workflow Templates",
                _feature_status(self._settings.features.workflow_templates),
                metadata=_feature_metadata("workflow_templates"),
            ),
            capability(
                "feature.capability_registry",
                "api",
                "Capability Registry",
                _feature_status(self._settings.features.capability_registry),
                metadata=_feature_metadata("capability_registry"),
            ),
            capability(
                "feature.python_analysis_enabled",
                "tool",
                "Python Analysis Execution",
                _python_analysis_feature_status(self._settings),
                risk_level="high",
                metadata={
                    **_feature_metadata("python_analysis_enabled"),
                    "executor": self._settings.features.python_analysis_executor,
                },
            ),
            capability(
                "feature.slot_code_string_isolation",
                "runtime",
                "Code-String Isolation",
                _code_string_isolation_status(self._settings),
                risk_level="high",
                metadata={
                    **_feature_metadata("slot_code_string_isolation"),
                    "requires": [
                        "python_analysis_enabled",
                        "python_analysis_executor=subprocess",
                    ],
                    "scope": "run_python_analysis code strings only",
                    "isolation_mode": _code_string_isolation_mode(self._settings),
                    "provider_contribution_isolation": "not_provided",
                },
            ),
            capability(
                "feature.slot_platform",
                "platform",
                "Slot Platform",
                _feature_status(self._settings.features.slot_platform),
                metadata=_feature_metadata("slot_platform"),
            ),
            capability(
                "feature.slot_governance",
                "governance",
                "Slot Governance",
                _feature_status(self._settings.features.slot_governance),
                metadata=_feature_metadata("slot_governance"),
            ),
            capability(
                "feature.slot_watcher",
                "runtime",
                "Slot Watcher",
                _feature_status(self._settings.features.slot_watcher),
                metadata=_feature_metadata("slot_watcher"),
            ),
            capability(
                "feature.slot_ui",
                "ui",
                "Slot UI",
                _feature_status(self._settings.features.slot_ui),
                metadata=_feature_metadata("slot_ui"),
            ),
            capability(
                "feature.slot_enforcement",
                "governance",
                "Slot Enforcement",
                _feature_status(self._settings.features.slot_enforcement),
                risk_level="medium",
                metadata=_feature_metadata("slot_enforcement"),
            ),
            capability(
                "feature.slot_runtime_interception",
                "runtime",
                "Slot Runtime Interception",
                _feature_status(self._settings.features.slot_runtime_interception),
                risk_level="medium",
                metadata=_feature_metadata("slot_runtime_interception"),
            ),
            capability(
                "feature.slot_loader",
                "platform",
                "Slot Loader",
                _feature_status(self._settings.features.slot_loader),
                risk_level="medium",
                metadata={
                    **_feature_metadata("slot_loader"),
                    "manifest_dirs": [str(path) for path in self._settings.slots.manifest_dirs],
                },
            ),
            capability(
                "feature.slot_install",
                "platform",
                "Slot Install",
                _feature_status(self._settings.features.slot_install),
                risk_level="high",
                metadata={
                    **_feature_metadata("slot_install"),
                    "install_dir": str(self._settings.slots.install_dir),
                    "trusted_signers": list(self._settings.slots.trusted_signers),
                    "enterprise_allowlist": list(self._settings.slots.enterprise_allowlist),
                },
            ),
            capability(
                "feature.slot_provider_execution",
                "platform",
                "Slot Provider Execution",
                _feature_status(self._settings.features.slot_provider_execution),
                risk_level="high",
                metadata={
                    **_feature_metadata("slot_provider_execution"),
                    "requires": [
                        "slot_platform",
                        "slot_loader",
                        "slot_install",
                        "slot_runtime_interception",
                        "trusted_publisher_signature",
                        "revocation_check",
                    ],
                    "sandbox": "in_process_runtime_interception_only",
                },
            ),
        ]


class ModelProviderCapabilityProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def collect(self, context: Any = None) -> list[dict[str, Any]]:
        return [
            provider_capability("provider.kimi", "Kimi / Moonshot", bool(self._settings.kimi.api_key)),
            provider_capability("provider.deepseek", "DeepSeek", bool(self._settings.deepseek.api_key)),
        ]


class ApiCapabilityProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def collect(self, context: Any = None) -> list[dict[str, Any]]:
        return [
            capability(
                "api.loopback",
                "api",
                "Loopback API",
                "available" if self._settings.api.bind_host in {"127.0.0.1", "localhost", "::1"} else "blocked",
            )
        ]


class MaturityCapabilityProvider:
    def __init__(self, path: Path) -> None:
        self._path = path

    def collect(self, context: Any = None) -> list[dict[str, Any]]:
        values = _read_maturity_values(self._path)
        production_ready = values.get("production_ready") == "true"
        stable_declaration = values.get("stable_declaration", "")
        return [
            capability(
                "maturity.production_ready",
                "maturity",
                "Production Readiness",
                "available" if production_ready else "blocked",
                risk_level="high",
                metadata={"source": str(self._path), "production_ready": production_ready},
            ),
            capability(
                "maturity.stable_declaration",
                "maturity",
                "Stable Declaration",
                "blocked" if stable_declaration == "forbidden" else "available",
                risk_level="high",
                metadata={"source": str(self._path), "stable_declaration": stable_declaration or "unknown"},
            ),
        ]


class ToolRegistryCapabilityProvider:
    def __init__(self, registry: "ToolRegistry") -> None:
        self._registry = registry

    def collect(self, context: Any = None) -> list[dict[str, Any]]:
        return [
            capability(
                f"tool.{record['tool_name']}",
                "tool",
                str(record["tool_name"]),
                str(record["status"]),
                risk_level=str(record["risk_level"]),
                requires_approval=bool(record["requires_approval"]),
                metadata={
                    "category": record["category"],
                    "description": record["description"],
                    **dict(record.get("metadata", {})),
                },
            )
            for record in self._registry.capability_records_for_context(context)
        ]


def capability(
    capability_id: str,
    kind: str,
    name: str,
    status: str,
    *,
    risk_level: str = "low",
    requires_approval: bool = False,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "capability_id": capability_id,
        "kind": kind,
        "name": name,
        "status": status,
        "risk_level": risk_level,
        "requires_approval": requires_approval,
        "metadata": metadata or {},
    }


def provider_capability(capability_id: str, name: str, configured: bool) -> dict[str, Any]:
    return capability(
        capability_id,
        "model_provider",
        name,
        "available" if configured else "unconfigured",
        risk_level="medium",
        metadata={"configured": configured},
    )


def _feature_status(enabled: bool) -> str:
    return "available" if enabled else "disabled"


def _python_analysis_feature_status(settings: Settings) -> str:
    if settings.features.python_analysis_enabled and settings.features.python_analysis_executor != "disabled":
        return "available"
    return "disabled"


def _code_string_isolation_status(settings: Settings) -> str:
    if not settings.features.slot_code_string_isolation:
        return "disabled"
    if os.name == "nt":
        return "available"
    return "blocked"


def _code_string_isolation_mode(settings: Settings) -> str:
    if not settings.features.slot_code_string_isolation:
        return "disabled"
    if os.name == "nt":
        return "windows_job_object"
    return "unavailable_non_windows_fail_closed"


def _feature_metadata(feature_name: str) -> dict[str, Any]:
    lifecycle = asdict(FEATURE_LIFECYCLES[feature_name])
    lifecycle["regression_commands"] = list(lifecycle["regression_commands"])
    return {"lifecycle": lifecycle}


def _read_maturity_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {"production_ready": "false", "stable_declaration": "missing"}
    text = path.read_text(encoding="utf-8")
    values: dict[str, str] = {}
    production = re.search(r"^\s*production_ready:\s*(true|false)\s*$", text, re.MULTILINE | re.IGNORECASE)
    stable = re.search(r"^\s*stable_declaration:\s*['\"]?([A-Za-z0-9_-]+)['\"]?\s*$", text, re.MULTILINE)
    if production:
        values["production_ready"] = production.group(1).lower()
    if stable:
        values["stable_declaration"] = stable.group(1).lower()
    return values
