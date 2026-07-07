from __future__ import annotations

from doge.core.domain.tool_policy import ToolCategory
from doge.platform.governance.slot import (
    CompositeToolEntitlementChecker,
    DefaultToolGovernanceChecker,
    ToolGovernancePolicySlot,
)
from doge.platform.slots import SlotContext, SlotType


def test_tool_governance_policy_slot_manifest() -> None:
    manifest = ToolGovernancePolicySlot().manifest()

    assert manifest.id == "governance.tool_policy"
    assert manifest.type is SlotType.GOVERNANCE
    assert manifest.owner == "governance-evaluation"
    assert manifest.feature_flags == ("slot_platform", "slot_governance")
    assert manifest.provides.capabilities == ("tool_entitlement", "approval_policy")
    assert manifest.permissions.risk_level == "low"


def test_tool_governance_policy_slot_contributes_entitlement_checker() -> None:
    context = SlotContext(
        settings=object(),
        feature_flags={"slot_platform": True, "slot_governance": True},
    )

    contribution = ToolGovernancePolicySlot().resolve(context)

    assert contribution.slot_id == "governance.tool_policy"
    assert len(contribution.governance_policies) == 1
    policy = contribution.governance_policies[0]
    assert policy.policy_id == "governance.tool_policy.default_entitlement"
    assert policy.kind == "tool_entitlement"
    checker = policy.entitlement_checker_factory(context)
    assert isinstance(checker, DefaultToolGovernanceChecker)
    assert checker.can_execute(None, "query_stock", ToolCategory.READ_ONLY) is True
    assert checker.can_execute(None, "blocked", ToolCategory.FORBIDDEN) is False
    assert checker.requires_approval(None, "publish", ToolCategory.HIGH_RISK) is True


def test_composite_tool_entitlement_checker_combines_denials_and_approvals() -> None:
    composite = CompositeToolEntitlementChecker([
        DefaultToolGovernanceChecker(),
        _OnlyReadOnlyChecker(),
    ])

    assert composite.can_execute(None, "stock_overview", ToolCategory.READ_ONLY) is True
    assert composite.can_execute(None, "portfolio_risk", ToolCategory.ANALYTICAL) is False
    assert composite.can_execute(None, "publish", ToolCategory.HIGH_RISK) is False
    assert composite.requires_approval(None, "publish", ToolCategory.HIGH_RISK) is True
    assert composite.redact_schema(
        None,
        {"function": {"name": "portfolio_risk"}},
        ToolCategory.ANALYTICAL,
    ) is None


class _OnlyReadOnlyChecker:
    def can_execute(self, context, tool_name, category):
        return category == ToolCategory.READ_ONLY

    def requires_approval(self, context, tool_name, category):
        return False

    def redact_schema(self, context, schema, category):
        if not self.can_execute(context, schema.get("function", {}).get("name", ""), category):
            return None
        return schema
