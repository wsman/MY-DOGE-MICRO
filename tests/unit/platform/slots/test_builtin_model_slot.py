"""Built-in model slot tests."""

from __future__ import annotations

from doge.bootstrap.runtime_factories.builtin_model_slot import ModelKimiAgentSdkSlot
from doge.infrastructure.agent.backends import KimiAgentSdkBackend
from doge.platform.slots import (
    SLOT_SERVICE_SECRET_PROVIDER,
    SlotContext,
    SlotType,
)


class _KimiSettings:
    general_model = "kimi-k2.6"

    @staticmethod
    def effective_base_url() -> str:
        return "https://example.invalid/v1"


class _Settings:
    kimi = _KimiSettings()


def test_manifest_declares_model_backend_slot() -> None:
    manifest = ModelKimiAgentSdkSlot().manifest()

    assert manifest.id == "model.kimi_agent_sdk"
    assert manifest.type is SlotType.MODEL
    assert manifest.feature_flags == ("slot_platform",)
    assert manifest.provides.capabilities == ("agent.backend",)
    assert manifest.permissions.network == "allow"
    assert manifest.permissions.secrets == ("kimi.api_key",)


def test_resolve_contributes_backend_factory_without_constructing_backend() -> None:
    context = SlotContext(settings=_Settings(), feature_flags={"slot_platform": True})

    contribution = ModelKimiAgentSdkSlot().resolve(context)

    assert contribution.slot_id == "model.kimi_agent_sdk"
    assert contribution.tools == ()
    assert contribution.executor is None
    assert len(contribution.model_backends) == 1
    backend = contribution.model_backends[0]
    assert backend.backend_id == "kimi_agent_sdk"
    assert backend.capabilities == ("agent.backend",)


def test_backend_factory_uses_secret_provider_from_locator() -> None:
    secret_provider = object()
    context = SlotContext(
        settings=_Settings(),
        feature_flags={"slot_platform": True},
        service_locator=lambda service_id: (
            secret_provider if service_id == SLOT_SERVICE_SECRET_PROVIDER else None
        ),
    )
    backend_factory = ModelKimiAgentSdkSlot().resolve(context).model_backends[0].factory

    backend = backend_factory(context)

    assert isinstance(backend, KimiAgentSdkBackend)
    assert backend._secret_provider is secret_provider
    assert backend._base_url == "https://example.invalid/v1"
    assert backend._model == "kimi-k2.6"
