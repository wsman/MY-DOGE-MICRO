from doge.application.use_cases.capability_registry import BuildCapabilityRegistry
from doge.application.capabilities.registry import (
    ApiCapabilityProvider,
    FeatureCapabilityProvider,
    MaturityCapabilityProvider,
    ModelProviderCapabilityProvider,
    ToolRegistryCapabilityProvider,
)
from doge.application.agent.tools import build_default_tool_registry
from doge.config import Settings
from doge.config.settings import DeepSeekConfig, FeatureConfig, KimiConfig
from doge.core.domain.tool_policy import ToolCategory


def test_capability_registry_redacts_provider_secrets_and_blocks_production_ready():
    settings = Settings(
        kimi=KimiConfig(api_key="moonshot-secret"),
        deepseek=DeepSeekConfig(api_key="deepseek-secret"),
        features=FeatureConfig(capability_registry=True, run_summary_api=True),
    )

    snapshot = BuildCapabilityRegistry(settings).build()
    text = repr(snapshot)
    capabilities = {item["capability_id"]: item for item in snapshot["capabilities"]}

    assert "moonshot-secret" not in text
    assert "deepseek-secret" not in text
    assert capabilities["provider.kimi"]["status"] == "available"
    assert capabilities["provider.kimi"]["metadata"] == {"configured": True}
    assert capabilities["feature.run_summary_api"]["status"] == "available"
    assert capabilities["maturity.production_ready"]["status"] == "blocked"
    assert capabilities["maturity.stable_declaration"]["status"] == "blocked"


def test_capability_provider_split_preserves_existing_non_tool_capabilities():
    settings = Settings(features=FeatureConfig(capability_registry=True, run_summary_api=True))
    direct = BuildCapabilityRegistry(settings).build()
    split = BuildCapabilityRegistry(
        settings,
        providers=[
            FeatureCapabilityProvider(settings),
            ModelProviderCapabilityProvider(settings),
            ApiCapabilityProvider(settings),
            MaturityCapabilityProvider(settings.project_root / "docs" / "progress" / "runtime-maturity.yaml"),
        ],
    ).build()

    assert _stable_snapshot(direct) == _stable_snapshot(split)


def test_tool_capability_provider_matches_default_tool_registry_schemas():
    registry = build_default_tool_registry()
    snapshot = BuildCapabilityRegistry(
        Settings(features=FeatureConfig(capability_registry=True)),
        providers=[ToolRegistryCapabilityProvider(registry)],
    ).build()

    schema_names = {schema["function"]["name"] for schema in registry.schemas}
    tool_caps = {
        item["capability_id"].replace("tool.", ""): item
        for item in snapshot["capabilities"]
        if item["kind"] == "tool"
    }

    assert set(tool_caps) == schema_names
    assert tool_caps["publish_investment_memo"]["requires_approval"] is True
    assert tool_caps["publish_investment_memo"]["risk_level"] == "high"
    assert tool_caps["propose_portfolio_rebalance"]["requires_approval"] is True
    assert tool_caps["stock_overview"]["requires_approval"] is False


def test_tool_capability_provider_uses_registry_entitlement_redaction():
    registry = build_default_tool_registry(entitlement_checker=_OnlyReadOnlyEntitlements())
    snapshot = BuildCapabilityRegistry(
        Settings(features=FeatureConfig(capability_registry=True)),
        providers=[ToolRegistryCapabilityProvider(registry)],
    ).build(context=object())
    capability_ids = {item["capability_id"] for item in snapshot["capabilities"]}

    assert "tool.stock_overview" in capability_ids
    assert "tool.portfolio_risk" not in capability_ids
    assert "tool.publish_investment_memo" not in capability_ids


def _stable_snapshot(snapshot):
    return [
        {
            key: value
            for key, value in item.items()
            if key not in {"generated_at", "snapshot_id"}
        }
        for item in snapshot["capabilities"]
    ]


class _OnlyReadOnlyEntitlements:
    def can_execute(self, context, tool_name, category):
        return category == ToolCategory.READ_ONLY

    def requires_approval(self, context, tool_name, category):
        return category == ToolCategory.HIGH_RISK

    def redact_schema(self, context, schema, category):
        if not self.can_execute(context, schema.get("function", {}).get("name", ""), category):
            return None
        return schema
