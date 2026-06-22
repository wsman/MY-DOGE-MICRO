"""Build redacted platform capability snapshots."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from doge.application.capabilities.registry import (
    ApiCapabilityProvider,
    FeatureCapabilityProvider,
    MaturityCapabilityProvider,
    ModelProviderCapabilityProvider,
)
from doge.config import Settings
from doge.core.ports.capability_provider import ICapabilityProvider


class BuildCapabilityRegistry:
    """Assemble safe capability discovery records for UI and SDK clients."""

    def __init__(self, settings: Settings, providers: list[ICapabilityProvider] | None = None) -> None:
        self._settings = settings
        self._providers = providers if providers is not None else _default_providers(settings)

    def build(self, context: Any = None) -> dict[str, Any]:
        generated_at = datetime.now(timezone.utc).isoformat()
        capabilities: list[dict[str, Any]] = []
        for provider in self._providers:
            capabilities.extend(provider.collect(context))
        counts: dict[str, int] = {}
        for capability in capabilities:
            counts[capability["status"]] = counts.get(capability["status"], 0) + 1
        snapshot_id = "cap-" + hashlib.sha256(
            repr([(item["capability_id"], item["status"]) for item in capabilities]).encode("utf-8")
        ).hexdigest()[:16]
        return {
            "snapshot_id": snapshot_id,
            "generated_at": generated_at,
            "redaction_version": "doge.capability_redaction.v1",
            "status_counts": counts,
            "capabilities": capabilities,
        }


def _default_providers(settings: Settings) -> list[ICapabilityProvider]:
    return [
        FeatureCapabilityProvider(settings),
        ModelProviderCapabilityProvider(settings),
        ApiCapabilityProvider(settings),
        MaturityCapabilityProvider(settings.project_root / "docs" / "progress" / "runtime-maturity.yaml"),
    ]
