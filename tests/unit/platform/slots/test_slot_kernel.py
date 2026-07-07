from __future__ import annotations

import pytest

from doge.platform.slots import (
    ISlot,
    SlotBundle,
    SlotConfigurationError,
    SlotContribution,
    SlotContext,
    SlotKernel,
    SlotPolicy,
    SlotRegistry,
    SlotType,
    load_slot_manifest,
)


class TrackingSlot(ISlot):
    def __init__(self, slot_id: str, calls: list[str]) -> None:
        self._manifest = load_slot_manifest(
            {
                "schema_version": 1,
                "id": slot_id,
                "name": slot_id.replace(".", " ").title(),
                "version": "1.0.0",
                "type": "tool",
                "owner": "test",
                "maturity": "experimental",
                "description": "Tracking slot for lifecycle tests.",
                "entrypoint": "tests.unit.platform.slots.test_slot_kernel.TrackingSlot",
                "provides": {"capabilities": [slot_id.replace(".", "_") + "_capability"]},
                "feature_flags": ["slot_platform"],
            }
        )
        self._calls = calls

    def manifest(self):
        return self._manifest

    def resolve(self, context: SlotContext) -> SlotContribution:
        return SlotContribution(slot_id=self._manifest.id)

    def start(self, context: SlotContext) -> None:
        self._calls.append(f"start:{self._manifest.id}")

    def stop(self, context: SlotContext) -> None:
        self._calls.append(f"stop:{self._manifest.id}")


def test_kernel_resolves_policy_enabled_contributions(
    stub_slot,
    second_stub_slot,
    slot_context_factory,
) -> None:
    registry = SlotRegistry()
    registry.register(stub_slot)
    registry.register(second_stub_slot)
    kernel = SlotKernel(
        registry,
        policy=SlotPolicy(enabled_slots=("market.core",)),
    )

    contributions = kernel.resolve_contributions(
        slot_context_factory({"slot_platform": True}),
        slot_type=SlotType.TOOL,
    )

    assert [contribution.slot_id for contribution in contributions] == ["market.core"]


def test_kernel_status_is_policy_aware(
    stub_slot,
    second_stub_slot,
    slot_context_factory,
) -> None:
    registry = SlotRegistry()
    registry.register(stub_slot)
    registry.register(second_stub_slot)
    kernel = SlotKernel(registry, policy=SlotPolicy(disabled_slots=("other.slot",)))

    statuses = {
        record.id: record.status
        for record in kernel.status(slot_context_factory({"slot_platform": True}))
    }

    assert statuses == {"market.core": "resolved", "other.slot": "disabled"}


def test_kernel_invokes_lifecycle_hooks_in_reverse_stop_order(slot_context_factory) -> None:
    calls: list[str] = []
    registry = SlotRegistry()
    registry.register(TrackingSlot("market.core", calls))
    registry.register(TrackingSlot("other.slot", calls))
    kernel = SlotKernel(registry)

    started = kernel.start(slot_context_factory({"slot_platform": True}))
    stopped = kernel.stop(slot_context_factory({"slot_platform": True}))

    assert [record.slot_id for record in started] == ["market.core", "other.slot"]
    assert [record.slot_id for record in stopped] == ["other.slot", "market.core"]
    assert calls == [
        "start:market.core",
        "start:other.slot",
        "stop:other.slot",
        "stop:market.core",
    ]


def test_kernel_rejects_duplicate_bundle_ids(stub_slot) -> None:
    registry = SlotRegistry()
    registry.register(stub_slot)

    with pytest.raises(SlotConfigurationError, match="duplicate slot bundle"):
        SlotKernel(
            registry,
            bundles=(
                SlotBundle(
                    id="bundle.local",
                    name="Local",
                    description="Local bundle",
                    slot_ids=("market.core",),
                ),
                SlotBundle(
                    id="bundle.local",
                    name="Local Duplicate",
                    description="Duplicate local bundle",
                    slot_ids=("market.core",),
                ),
            ),
        )


def test_kernel_rejects_bundle_unknown_slot(stub_slot) -> None:
    registry = SlotRegistry()
    registry.register(stub_slot)

    with pytest.raises(SlotConfigurationError, match="unknown slot"):
        SlotKernel(
            registry,
            bundles=(
                SlotBundle(
                    id="bundle.local",
                    name="Local",
                    description="Local bundle",
                    slot_ids=("missing.slot",),
                ),
            ),
        )


def test_kernel_reports_bundle_status(
    stub_slot,
    second_stub_slot,
    slot_context_factory,
) -> None:
    registry = SlotRegistry()
    registry.register(stub_slot)
    registry.register(second_stub_slot)
    kernel = SlotKernel(
        registry,
        policy=SlotPolicy(disabled_slots=("other.slot",)),
        bundles=(
            SlotBundle(
                id="bundle.local",
                name="Local",
                description="Local bundle",
                slot_ids=("market.core", "other.slot"),
            ),
        ),
    )

    [row] = kernel.bundle_status(slot_context_factory({"slot_platform": True}))

    assert row.id == "bundle.local"
    assert row.status == "partial"
    assert row.enabled_slot_ids == ("market.core",)
    assert row.disabled_slot_ids == ("other.slot",)
