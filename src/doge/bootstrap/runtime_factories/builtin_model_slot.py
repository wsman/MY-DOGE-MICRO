"""Built-in model slots for runtime factory wiring."""

from __future__ import annotations

from doge.infrastructure.agent.backends import KimiAgentSdkBackend
from doge.platform.slots import (
    SCHEMA_VERSION,
    ISlot,
    ModelBackendContribution,
    SLOT_SERVICE_SECRET_PROVIDER,
    SlotCompatibility,
    SlotContribution,
    SlotContext,
    SlotHealth,
    SlotManifest,
    SlotPermissions,
    SlotProvides,
    SlotType,
)

_MANIFEST = SlotManifest(
    schema_version=SCHEMA_VERSION,
    id="model.kimi_agent_sdk",
    name="Kimi Agent SDK",
    version="1.0.0",
    type=SlotType.MODEL,
    owner="agent-runtime",
    maturity="experimental",
    description=(
        "Provides the kimi_agent_sdk agent backend used by agent automation "
        "execution profiles."
    ),
    entrypoint="doge.bootstrap.runtime_factories.builtin_model_slot.ModelKimiAgentSdkSlot",
    provides=SlotProvides(capabilities=("agent.backend",)),
    permissions=SlotPermissions(network="allow", secrets=("kimi.api_key",), risk_level="medium"),
    health=SlotHealth(status="experimental"),
    feature_flags=("slot_platform",),
    compatibility=SlotCompatibility(runtime_min="1"),
)


class ModelKimiAgentSdkSlot(ISlot):
    """Built-in model slot wrapping the existing Kimi Agent SDK backend factory."""

    def manifest(self) -> SlotManifest:
        return _MANIFEST

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id="model.kimi_agent_sdk",
            model_backends=(
                ModelBackendContribution(
                    backend_id="kimi_agent_sdk",
                    factory=_build_backend,
                    capabilities=("agent.backend",),
                    profiles=("agent_automation",),
                ),
            ),
        )


def _build_backend(context: SlotContext) -> KimiAgentSdkBackend:
    return KimiAgentSdkBackend(
        base_url=context.settings.kimi.effective_base_url(),
        model=context.settings.kimi.general_model,
        secret_provider=context.locate(SLOT_SERVICE_SECRET_PROVIDER),
    )
