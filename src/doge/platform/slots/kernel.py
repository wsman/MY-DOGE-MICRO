"""First-class slot orchestration kernel."""

from __future__ import annotations

from typing import Iterable

from doge.platform.slots.bundles import SlotBundle, SlotBundleStatus
from doge.platform.slots.contracts import (
    SlotContribution,
    SlotContext,
    SlotStatus,
)
from doge.platform.slots.enforcement import SlotEnforcementPolicy
from doge.platform.slots.errors import SlotConfigurationError, UnknownSlotError
from doge.platform.slots.lifecycle import SlotLifecycle, SlotLifecycleRecord
from doge.platform.slots.manifest import SlotHealth, SlotType
from doge.platform.slots.policy import SlotPolicy
from doge.platform.slots.registry import SlotRegistry, SlotStatusRecord


class SlotKernel:
    """Orchestrates registry, policy, lifecycle, bundles, and contribution resolve."""

    def __init__(
        self,
        registry: SlotRegistry,
        *,
        policy: SlotPolicy | None = None,
        bundles: Iterable[SlotBundle] = (),
        lifecycle: SlotLifecycle | None = None,
        enforcement: SlotEnforcementPolicy | None = None,
    ) -> None:
        self._registry = registry
        self._policy = policy or SlotPolicy()
        self._lifecycle = lifecycle or SlotLifecycle()
        self._enforcement = enforcement or SlotEnforcementPolicy()
        self._bundles = _index_bundles(tuple(bundles))
        self._validate_bundles()

    @property
    def registry(self) -> SlotRegistry:
        return self._registry

    @property
    def policy(self) -> SlotPolicy:
        return self._policy

    @property
    def lifecycle(self) -> SlotLifecycle:
        return self._lifecycle

    @property
    def enforcement(self) -> SlotEnforcementPolicy:
        return self._enforcement

    def bundles(self) -> tuple[SlotBundle, ...]:
        return tuple(self._bundles.values())

    def get_bundle(self, bundle_id: str) -> SlotBundle:
        try:
            return self._bundles[bundle_id]
        except KeyError as exc:
            raise UnknownSlotError(f"unknown slot bundle: {bundle_id}") from exc

    def status(self, context: SlotContext) -> tuple[SlotStatusRecord, ...]:
        """Return policy-aware status records for all registered slots."""

        records: list[SlotStatusRecord] = []
        for slot in self._registry.all():
            manifest = slot.manifest()
            health = self._health_for(slot, context)
            status = (
                SlotStatus.RESOLVED.value
                if self._slot_allowed(slot, context, health=health)
                else SlotStatus.DISABLED.value
            )
            records.append(
                SlotStatusRecord(
                    id=manifest.id,
                    name=manifest.name,
                    type=manifest.type.value,
                    status=status,
                    tools_count=len(manifest.provides.tools),
                    health=health.status,
                    feature_flags=manifest.feature_flags,
                )
            )
        return tuple(records)

    def bundle_status(self, context: SlotContext) -> tuple[SlotBundleStatus, ...]:
        """Return read-only status rows for registered bundles."""

        rows: list[SlotBundleStatus] = []
        for bundle in self._bundles.values():
            missing: list[str] = []
            enabled: list[str] = []
            disabled: list[str] = list(bundle.disabled_slot_ids)
            for slot_id in bundle.slot_ids:
                try:
                    slot = self._registry.get(slot_id)
                except UnknownSlotError:
                    missing.append(slot_id)
                    continue
                if self._slot_allowed(slot, context):
                    enabled.append(slot_id)
                else:
                    disabled.append(slot_id)
            status = _bundle_status(enabled, disabled, missing)
            rows.append(
                SlotBundleStatus(
                    id=bundle.id,
                    name=bundle.name,
                    description=bundle.description,
                    status=status,
                    slot_ids=bundle.slot_ids,
                    enabled_slot_ids=tuple(enabled),
                    disabled_slot_ids=tuple(disabled),
                    missing_slot_ids=tuple(missing),
                    maturity=bundle.maturity,
                )
            )
        return tuple(rows)

    def resolve_contributions(
        self,
        context: SlotContext,
        *,
        slot_type: SlotType | None = None,
    ) -> tuple[SlotContribution, ...]:
        """Resolve enabled contributions, optionally restricted to one slot type."""

        contributions: list[SlotContribution] = []
        for slot in self._registry.all():
            manifest = slot.manifest()
            if slot_type is not None and manifest.type is not slot_type:
                continue
            if not self._slot_allowed(slot, context):
                continue
            contributions.append(slot.resolve(context))
        return tuple(contributions)

    def start(
        self,
        context: SlotContext,
        *,
        slot_type: SlotType | None = None,
    ) -> tuple[SlotLifecycleRecord, ...]:
        """Invoke ``ISlot.start`` for enabled slots."""

        records: list[SlotLifecycleRecord] = []
        for slot in self._registry.all():
            manifest = slot.manifest()
            if slot_type is not None and manifest.type is not slot_type:
                continue
            if not self._slot_allowed(slot, context):
                continue
            records.append(self._lifecycle.start(slot, context))
        return tuple(records)

    def stop(self, context: SlotContext) -> tuple[SlotLifecycleRecord, ...]:
        """Stop started slots in reverse start order."""

        records: list[SlotLifecycleRecord] = []
        for slot_id in reversed(self._lifecycle.started_slot_ids()):
            records.append(self._lifecycle.stop(self._registry.get(slot_id), context))
        return tuple(records)

    def _validate_bundles(self) -> None:
        for bundle in self._bundles.values():
            unknown = [
                slot_id
                for slot_id in (*bundle.slot_ids, *bundle.disabled_slot_ids)
                if not self._registry_has(slot_id)
            ]
            if unknown:
                raise SlotConfigurationError(
                    f"slot bundle {bundle.id} references unknown slot(s): "
                    + ", ".join(sorted(unknown))
                )

    def _registry_has(self, slot_id: str) -> bool:
        try:
            self._registry.get(slot_id)
        except UnknownSlotError:
            return False
        return True

    def _slot_allowed(
        self,
        slot: object,
        context: SlotContext,
        *,
        health: SlotHealth | None = None,
    ) -> bool:
        manifest = slot.manifest()  # type: ignore[attr-defined]
        if not self._policy.allows(manifest, context):
            return False
        decision = self._enforcement.check(
            manifest,
            context,
            health=health or self._health_for(slot, context),
        )
        return decision.allowed

    def _health_for(self, slot: object, context: SlotContext) -> SlotHealth:
        manifest = slot.manifest()  # type: ignore[attr-defined]
        if not self._enforcement.enforce_health:
            return manifest.health
        try:
            return slot.health(context)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001 - health probes must degrade safely
            return SlotHealth(
                status="degraded",
                notes=f"health check failed: {exc}",
            )


def _index_bundles(bundles: tuple[SlotBundle, ...]) -> dict[str, SlotBundle]:
    indexed: dict[str, SlotBundle] = {}
    for bundle in bundles:
        if bundle.id in indexed:
            raise SlotConfigurationError(f"duplicate slot bundle: {bundle.id}")
        indexed[bundle.id] = bundle
    return indexed


def _bundle_status(enabled: list[str], disabled: list[str], missing: list[str]) -> str:
    if missing:
        return "invalid"
    if enabled and disabled:
        return "partial"
    if enabled:
        return "resolved"
    return "disabled"
