"""Slot permission and health enforcement policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from doge.platform.slots.contracts import SlotContext
from doge.platform.slots.manifest import SlotHealth, SlotManifest


@dataclass(frozen=True)
class SlotEnforcementDecision:
    """Decision produced by slot enforcement before resolve/start."""

    allowed: bool
    reason: str = ""


@dataclass(frozen=True)
class SlotEnforcementPolicy:
    """Runtime guard for declarative slot permissions and health.

    The default is intentionally inert so existing local-alpha behavior remains
    byte-equivalent unless bootstrap enables enforcement explicitly.
    """

    enforce_permissions: bool = False
    enforce_health: bool = False
    allow_shell: bool = False
    allow_forbidden_risk: bool = False
    allow_degraded_health: bool = True
    allow_disabled_health: bool = False

    def check(
        self,
        manifest: SlotManifest,
        context: SlotContext,
        *,
        health: SlotHealth | None = None,
    ) -> SlotEnforcementDecision:
        """Return whether a slot may resolve/start under this policy."""

        delegated = _delegated_decision(context.permission_checker, manifest, context, health)
        if delegated is not None:
            return delegated

        if self.enforce_permissions:
            permission_decision = self._check_permissions(manifest)
            if not permission_decision.allowed:
                return permission_decision

        if self.enforce_health:
            health_decision = self._check_health(health or manifest.health)
            if not health_decision.allowed:
                return health_decision

        return SlotEnforcementDecision(True)

    def _check_permissions(self, manifest: SlotManifest) -> SlotEnforcementDecision:
        permissions = manifest.permissions
        if permissions.risk_level == "forbidden" and not self.allow_forbidden_risk:
            return SlotEnforcementDecision(
                False,
                f"slot {manifest.id} declares forbidden risk",
            )
        if permissions.shell == "allow" and not self.allow_shell:
            return SlotEnforcementDecision(
                False,
                f"slot {manifest.id} declares shell permission",
            )
        return SlotEnforcementDecision(True)

    def _check_health(self, health: SlotHealth) -> SlotEnforcementDecision:
        if health.status == "disabled" and not self.allow_disabled_health:
            return SlotEnforcementDecision(False, "slot health is disabled")
        if health.status == "degraded" and not self.allow_degraded_health:
            return SlotEnforcementDecision(False, "slot health is degraded")
        return SlotEnforcementDecision(True)


def _delegated_decision(
    checker: Any,
    manifest: SlotManifest,
    context: SlotContext,
    health: SlotHealth | None,
) -> SlotEnforcementDecision | None:
    if checker is None or not hasattr(checker, "check_slot_manifest"):
        return None
    raw = checker.check_slot_manifest(manifest, context=context, health=health)
    if isinstance(raw, SlotEnforcementDecision):
        return raw
    if isinstance(raw, bool):
        return SlotEnforcementDecision(raw, "" if raw else "slot permission checker denied")
    if isinstance(raw, tuple) and raw:
        allowed = bool(raw[0])
        reason = str(raw[1]) if len(raw) > 1 else ""
        return SlotEnforcementDecision(allowed, reason)
    if hasattr(raw, "allowed"):
        return SlotEnforcementDecision(
            bool(raw.allowed),
            str(getattr(raw, "reason", "")),
        )
    return None
