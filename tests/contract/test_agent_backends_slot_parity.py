"""Agent backend slot parity tests for Sprint 034."""

from __future__ import annotations

import pytest

from doge.bootstrap.runtime_factories import runtime_kernel
from doge.bootstrap.runtime_factories import slots as slots_module
from doge.config import reset_settings
from doge.infrastructure.agent.backends import KimiAgentSdkBackend
from doge.platform.slots import (
    ISlot,
    ModelBackendContribution,
    SlotConfigurationError,
    SlotContribution,
    SlotContext,
    SlotHealth,
    SlotManifest,
    SlotProvides,
    SlotRegistry,
    SlotType,
)

_ALL_FEATURE_VARS = [
    "DOGE_FEATURE_RUN_SUMMARY_API",
    "DOGE_FEATURE_PLATFORM_OBJECTS",
    "DOGE_FEATURE_WORKFLOW_TEMPLATES",
    "DOGE_FEATURE_CAPABILITY_REGISTRY",
    "DOGE_FEATURE_RUNTIME_OUTBOX_PUBLISHER",
    "DOGE_FEATURE_PYTHON_ANALYSIS_ENABLED",
    "DOGE_FEATURE_SLOT_PLATFORM",
]


class _FakeGateway:
    def __init__(self, secret_provider: object) -> None:
        self._secret_provider = secret_provider

    def build_secret_provider(self):
        return self._secret_provider


class _DuplicateBackendSlot(ISlot):
    def __init__(self, slot_id: str) -> None:
        self._manifest = SlotManifest(
            schema_version=1,
            id=slot_id,
            name="Duplicate Backend Slot",
            version="1.0.0",
            type=SlotType.MODEL,
            owner="slot-tests",
            maturity="experimental",
            description="Stub model slot with duplicate backend id.",
            entrypoint="tests.contract.test_agent_backends_slot_parity.DuplicateBackendSlot",
            provides=SlotProvides(capabilities=("agent.backend",)),
            health=SlotHealth(status="experimental"),
            feature_flags=("slot_platform",),
        )

    def manifest(self) -> SlotManifest:
        return self._manifest

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(
            slot_id=self._manifest.id,
            model_backends=(
                ModelBackendContribution("duplicate.backend", lambda _ctx: object()),
            ),
        )


@pytest.fixture
def secret_provider() -> object:
    return object()


@pytest.fixture
def fake_gateway(secret_provider):
    return _FakeGateway(secret_provider)


def _strip_feature_env(monkeypatch, keep: set[str] | None = None) -> None:
    keep = keep or set()
    for var in _ALL_FEATURE_VARS:
        if var not in keep:
            monkeypatch.delenv(var, raising=False)


def _backend_summary(backends: dict[str, object]) -> dict[str, type]:
    return {name: type(backend) for name, backend in backends.items()}


def test_build_agent_backends_flag_on_matches_flag_off(monkeypatch, fake_gateway, secret_provider) -> None:
    _strip_feature_env(monkeypatch)
    reset_settings()
    off = runtime_kernel.build_agent_backends(lambda: fake_gateway, secret_provider)

    _strip_feature_env(monkeypatch, keep={"DOGE_FEATURE_SLOT_PLATFORM"})
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()
    on = runtime_kernel.build_agent_backends(lambda: fake_gateway, secret_provider)

    assert _backend_summary(on) == _backend_summary(off) == {
        "kimi_agent_sdk": KimiAgentSdkBackend
    }
    assert on["kimi_agent_sdk"]._secret_provider is secret_provider


def test_slot_aware_agent_backends_matches_public_flag_branch(monkeypatch, fake_gateway, secret_provider) -> None:
    _strip_feature_env(monkeypatch, keep={"DOGE_FEATURE_SLOT_PLATFORM"})
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()

    direct = slots_module.build_slot_aware_agent_backends(lambda: fake_gateway, secret_provider)
    public = runtime_kernel.build_agent_backends(lambda: fake_gateway, secret_provider)

    assert _backend_summary(direct) == _backend_summary(public) == {
        "kimi_agent_sdk": KimiAgentSdkBackend
    }


def test_slot_aware_agent_backends_does_not_build_gateway_when_secret_provider_supplied(
    monkeypatch,
    secret_provider,
) -> None:
    _strip_feature_env(monkeypatch, keep={"DOGE_FEATURE_SLOT_PLATFORM"})
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()

    def fail_if_called():
        raise AssertionError("gateway_container_fn should not be called")

    backends = slots_module.build_slot_aware_agent_backends(
        fail_if_called,
        secret_provider,
    )

    assert _backend_summary(backends) == {"kimi_agent_sdk": KimiAgentSdkBackend}
    assert backends["kimi_agent_sdk"]._secret_provider is secret_provider


def test_duplicate_model_backend_ids_fail_fast(monkeypatch, fake_gateway, secret_provider) -> None:
    registry = SlotRegistry()
    registry.register(_DuplicateBackendSlot("model.duplicate_a"))
    registry.register(_DuplicateBackendSlot("model.duplicate_b"))
    monkeypatch.setattr(slots_module, "build_builtin_slot_registry", lambda: registry)
    _strip_feature_env(monkeypatch, keep={"DOGE_FEATURE_SLOT_PLATFORM"})
    monkeypatch.setenv("DOGE_FEATURE_SLOT_PLATFORM", "1")
    reset_settings()

    with pytest.raises(SlotConfigurationError, match="duplicate.backend"):
        slots_module.build_slot_aware_agent_backends(lambda: fake_gateway, secret_provider)
