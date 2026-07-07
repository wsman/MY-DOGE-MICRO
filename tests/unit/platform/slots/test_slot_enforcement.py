from __future__ import annotations

from doge.platform.slots import (
    ISlot,
    SlotContribution,
    SlotContext,
    SlotEnforcementPolicy,
    SlotHealth,
    SlotKernel,
    SlotRegistry,
    SlotType,
    load_slot_manifest,
)


class _HealthSlot(ISlot):
    def __init__(self, health: SlotHealth) -> None:
        self.calls = 0
        self._health = health
        self._manifest = load_slot_manifest(
            {
                "schema_version": 1,
                "id": "health.probe",
                "name": "Health Probe",
                "version": "1.0.0",
                "type": "tool",
                "owner": "slot-tests",
                "maturity": "experimental",
                "description": "Health probe slot.",
                "entrypoint": "tests.unit.platform.slots.test_slot_enforcement.HealthSlot",
                "provides": {"capabilities": ["health_probe"]},
                "feature_flags": ["slot_platform"],
            }
        )

    def manifest(self):
        return self._manifest

    def health(self, context: SlotContext) -> SlotHealth:
        self.calls += 1
        return self._health

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(slot_id=self._manifest.id)


def test_enforcement_policy_blocks_shell_permission(slot_context_factory) -> None:
    manifest = load_slot_manifest(
        {
            "schema_version": 1,
            "id": "tool.shell",
            "name": "Shell Tool",
            "version": "1.0.0",
            "type": "tool",
            "owner": "slot-tests",
            "maturity": "experimental",
            "description": "Shell slot.",
            "entrypoint": "tests.unit.platform.slots.test_slot_enforcement.ShellSlot",
            "provides": {"capabilities": ["tool_shell"]},
            "permissions": {"shell": "allow", "risk_level": "low"},
            "feature_flags": ["slot_platform"],
        }
    )

    decision = SlotEnforcementPolicy(enforce_permissions=True).check(
        manifest,
        slot_context_factory({"slot_platform": True}),
    )

    assert decision.allowed is False
    assert "shell permission" in decision.reason


def test_kernel_blocks_disabled_active_health() -> None:
    slot = _HealthSlot(SlotHealth(status="disabled", notes="offline"))
    registry = SlotRegistry()
    registry.register(slot)
    kernel = SlotKernel(
        registry,
        enforcement=SlotEnforcementPolicy(enforce_health=True),
    )
    context = SlotContext(settings=object(), feature_flags={"slot_platform": True})

    [status] = kernel.status(context)
    contributions = kernel.resolve_contributions(context, slot_type=SlotType.TOOL)

    assert status.status == "disabled"
    assert status.health == "disabled"
    assert contributions == ()
    assert slot.calls >= 1


def test_kernel_reports_degraded_health_without_blocking_by_default() -> None:
    slot = _HealthSlot(SlotHealth(status="degraded", notes="slow"))
    registry = SlotRegistry()
    registry.register(slot)
    kernel = SlotKernel(
        registry,
        enforcement=SlotEnforcementPolicy(enforce_health=True),
    )
    context = SlotContext(settings=object(), feature_flags={"slot_platform": True})

    [status] = kernel.status(context)
    [contribution] = kernel.resolve_contributions(context, slot_type=SlotType.TOOL)

    assert status.status == "resolved"
    assert status.health == "degraded"
    assert contribution.slot_id == "health.probe"
